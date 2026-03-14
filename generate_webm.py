"""Generate a minimal valid WebM file with a playable VP8 keyframe.

This creates a 2x2 pixel green WebM file that Chromium can decode.
The VP8 keyframe bitstream is carefully constructed per RFC 6386.
"""
import struct
import io
import base64
import sys


def ebml_element(element_id: bytes, data: bytes) -> bytes:
    """Build an EBML element: ID + size + data."""
    return element_id + ebml_encode_size(len(data)) + data


def ebml_encode_size(size: int) -> bytes:
    """Encode size using EBML variable-length integer."""
    if size < 0x7F:
        return bytes([size | 0x80])
    elif size < 0x3FFF:
        return bytes([(size >> 8) | 0x40, size & 0xFF])
    elif size < 0x1FFFFF:
        return bytes([(size >> 16) | 0x20, (size >> 8) & 0xFF, size & 0xFF])
    elif size < 0x0FFFFFFF:
        return bytes([(size >> 24) | 0x10, (size >> 16) & 0xFF, (size >> 8) & 0xFF, size & 0xFF])
    else:
        return bytes([
            0x01,
            (size >> 48) & 0xFF, (size >> 40) & 0xFF, (size >> 32) & 0xFF,
            (size >> 24) & 0xFF, (size >> 16) & 0xFF, (size >> 8) & 0xFF,
            size & 0xFF,
        ])


def ebml_encode_unknown_size() -> bytes:
    """Encode unknown/streaming size for Segment."""
    return bytes([0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])


def uint_bytes(val: int, nbytes: int) -> bytes:
    return val.to_bytes(nbytes, "big")


def make_vp8_keyframe(width: int = 2, height: int = 2) -> bytes:
    """Create a minimal valid VP8 keyframe bitstream.
    
    The approach: use a boolean arithmetic coder to produce valid
    VP8 partition data for a minimal frame.
    """
    # Bool encoder state
    class BoolEncoder:
        def __init__(self):
            self.low = 0
            self.range = 255
            self.count = -24
            self.buffer = bytearray()
        
        def encode_bool(self, value: int, prob: int):
            split = 1 + (((self.range - 1) * prob) >> 8)
            if value:
                self.low += split
                self.range -= split
            else:
                self.range = split
            
            shift = self._norm_shift()
            self.range <<= shift
            self.count += shift
            self.low <<= shift
            
            if self.count >= 0:
                offset = self.low >> 24
                self.buffer.append(offset & 0xFF)
                self.low = (self.low & 0xFFFFFF) # keep lower 24 bits
                self.count -= 8
        
        def _norm_shift(self):
            shift = 0
            while self.range < 128:
                self.range <<= 1
                shift += 1
            return shift
        
        def encode_literal(self, value: int, nbits: int):
            for i in range(nbits - 1, -1, -1):
                self.encode_bool((value >> i) & 1, 128)
        
        def flush(self):
            # Flush remaining bits
            for _ in range(32):
                self.encode_bool(0, 128)
            # Ensure at least a few bytes
            if len(self.buffer) == 0:
                self.buffer.append(0)
            return bytes(self.buffer)
    
    enc = BoolEncoder()
    
    # --- Frame header (Section 9.2-9.11 of RFC 6386) ---
    # color_space = 0 (YUV)
    enc.encode_bool(0, 128)
    # clamping_type = 0 (clamped)
    enc.encode_bool(0, 128)
    
    # segmentation_enabled = 0
    enc.encode_bool(0, 128)
    
    # filter_type = 0 (normal)
    enc.encode_bool(0, 128)
    # loop_filter_level = 0 (6 bits)
    enc.encode_literal(0, 6)
    # sharpness_level = 0 (3 bits)
    enc.encode_literal(0, 3)
    
    # log2_nbr_of_dct_partitions = 0 (2 bits) -> 1 partition
    enc.encode_literal(0, 2)
    
    # --- Dequantization indices (Section 9.6) ---
    # y_ac_qi (7-bit index)
    enc.encode_literal(4, 7)
    # y_dc_delta present = 0
    enc.encode_bool(0, 128)
    # y2_dc_delta present = 0
    enc.encode_bool(0, 128)
    # y2_ac_delta present = 0
    enc.encode_bool(0, 128)
    # uv_dc_delta present = 0
    enc.encode_bool(0, 128)
    # uv_ac_delta present = 0
    enc.encode_bool(0, 128)
    
    # --- Refresh entropy probs = 0 (Section 9.11) ---
    enc.encode_bool(0, 128)
    
    # --- Token probability updates (Section 9.9) ---
    # For key frames: 4 types x 8 bands x 3 contexts x 11 probs
    # All update flags = 0 (no updates, use defaults)
    for _type in range(4):
        for _band in range(8):
            for _ctx in range(3):
                for _prob in range(11):
                    enc.encode_bool(0, 252)  # prob of update, 252 = very unlikely
    
    # --- mb_no_coeff_skip = 1 ---
    enc.encode_bool(1, 128)
    # prob_skip_false (8 bits) - probability that a macroblock has nonzero coefficients
    enc.encode_literal(1, 8)  # 1 = almost certainly skip
    
    # --- Macroblock data ---
    # For 2x2 image: 1 macroblock (16x16 covers it)
    # Number of MBs: ceil(width/16) * ceil(height/16) = 1
    
    # For each MB:
    # mb_skip_coeff = 1 (skip, prob = prob_skip_false=1, so bool with prob=1)
    enc.encode_bool(1, 1)  # skip this macroblock
    
    # Intra prediction mode for Y (luma):
    # Mode B_PRED=0, DC_PRED=1 encoded via tree
    # Use DC_PRED for simplicity
    # kf_ymode_tree: B_PRED(0), TM_PRED(1), VP8_MV_ZERO, V_PRED(2), H_PRED(3), DC_PRED(4)
    # The tree structure from the spec:
    # kf_ymode_prob = [145, 156, 163, 128]
    # Tree: 
    #   0: branch prob[0] -> 0=B_PRED, 1=go to 2
    #   2: branch prob[1] -> 0=TM_PRED, 1=go to 4
    #   4: branch prob[2] -> 0=V_PRED, 1=go to 6
    #   6: branch prob[3] -> 0=H_PRED, 1=DC_PRED
    
    # For DC_PRED (mode 4): need path 1,1,1,1
    enc.encode_bool(1, 145)  # not B_PRED
    enc.encode_bool(1, 156)  # not TM_PRED
    enc.encode_bool(1, 163)  # not V_PRED
    enc.encode_bool(1, 128)  # DC_PRED (right branch)
    
    # Chroma intra prediction mode:
    # kf_uv_mode_tree with probs [142, 114, 183]
    # DC_PRED(0): take left branch at first node
    enc.encode_bool(0, 142)  # DC_PRED for chroma
    
    bool_data = enc.flush()
    
    # DCT partition - since all macroblocks are skipped, this is empty
    dct_data = bytes([0x00])
    
    # --- Uncompressed data chunk (10 bytes for key frame) ---
    first_part_size = len(bool_data)
    
    # Frame tag (3 bytes):
    # Bit 0: frame_type = 0 (key frame)
    # Bits 1-2: version = 0
    # Bit 3: show_frame = 1
    # Bits 4-23: first_part_size (19 bits, split across 3 bytes)
    tag = (0 << 0) | (0 << 1) | (1 << 3) | ((first_part_size & 0x7FFFF) << 5)
    tag_bytes = struct.pack("<I", tag)[:3]
    
    # Start code (3 bytes)
    start_code = bytes([0x9D, 0x01, 0x2A])
    
    # Horizontal size info (2 bytes LE): width | (scale << 14)
    horiz = struct.pack("<H", width & 0x3FFF)
    
    # Vertical size info (2 bytes LE): height | (scale << 14)
    vert = struct.pack("<H", height & 0x3FFF)
    
    frame = tag_bytes + start_code + horiz + vert + bool_data + dct_data
    return frame


def make_webm(vp8_frame: bytes, width: int = 2, height: int = 2) -> bytes:
    """Wrap a VP8 keyframe in a WebM container."""
    buf = io.BytesIO()
    
    # --- EBML Header ---
    ebml_body = b""
    ebml_body += ebml_element(b"\x42\x86", uint_bytes(1, 1))  # EBMLVersion
    ebml_body += ebml_element(b"\x42\xf7", uint_bytes(1, 1))  # EBMLReadVersion
    ebml_body += ebml_element(b"\x42\xf2", uint_bytes(4, 1))  # EBMLMaxIDLength
    ebml_body += ebml_element(b"\x42\xf3", uint_bytes(8, 1))  # EBMLMaxSizeLength
    ebml_body += ebml_element(b"\x42\x82", b"webm")           # DocType
    ebml_body += ebml_element(b"\x42\x87", uint_bytes(4, 1))  # DocTypeVersion
    ebml_body += ebml_element(b"\x42\x85", uint_bytes(2, 1))  # DocTypeReadVersion
    buf.write(ebml_element(b"\x1a\x45\xdf\xa3", ebml_body))
    
    # --- Segment (unknown size for streaming) ---
    segment_start = buf.tell()
    buf.write(b"\x18\x53\x80\x67")  # Segment element ID
    # We'll use known size - compute segment body first
    segment_body = io.BytesIO()
    
    # --- Info element ---
    info_body = b""
    info_body += ebml_element(b"\x2a\xd7\xb1", uint_bytes(1000000, 3))  # TimecodeScale: 1ms
    info_body += ebml_element(b"\x44\x89", struct.pack(">d", 0.0))      # Duration: 0
    info_body += ebml_element(b"\x4d\x80", b"mock")                      # MuxingApp
    info_body += ebml_element(b"\x57\x41", b"mock")                      # WritingApp
    segment_body.write(ebml_element(b"\x15\x49\xa9\x66", info_body))
    
    # --- Tracks element ---
    track_entry = b""
    track_entry += ebml_element(b"\xd7", uint_bytes(1, 1))          # TrackNumber
    track_entry += ebml_element(b"\x73\xc5", uint_bytes(1, 1))      # TrackUID
    track_entry += ebml_element(b"\x83", uint_bytes(1, 1))           # TrackType: video=1
    track_entry += ebml_element(b"\x86", b"V_VP8")                   # CodecID
    
    # Video settings
    video_body = b""
    video_body += ebml_element(b"\xb0", uint_bytes(width, 2))       # PixelWidth
    video_body += ebml_element(b"\xba", uint_bytes(height, 2))      # PixelHeight
    track_entry += ebml_element(b"\xe0", video_body)
    
    tracks_body = ebml_element(b"\xae", track_entry)
    segment_body.write(ebml_element(b"\x16\x54\xae\x6b", tracks_body))
    
    # --- Cluster ---
    cluster_body = b""
    cluster_body += ebml_element(b"\xe7", uint_bytes(0, 1))  # Timecode: 0
    
    # SimpleBlock: track=1, timecode=0, keyframe flag
    block_header = bytes([0x81])  # Track number 1 (EBML coded)
    block_header += struct.pack(">h", 0)  # Relative timecode: 0
    block_header += bytes([0x80])  # Flags: keyframe
    simple_block = block_header + vp8_frame
    cluster_body += ebml_element(b"\xa3", simple_block)
    
    segment_body.write(ebml_element(b"\x1f\x43\xb6\x75", cluster_body))
    
    # Write segment with known size
    seg_data = segment_body.getvalue()
    buf.write(ebml_encode_size(len(seg_data)))
    buf.write(seg_data)
    
    return buf.getvalue()


if __name__ == "__main__":
    vp8_frame = make_vp8_keyframe(2, 2)
    webm_data = make_webm(vp8_frame, 2, 2)
    
    print(f"VP8 frame size: {len(vp8_frame)} bytes")
    print(f"WebM file size: {len(webm_data)} bytes")
    print(f"VP8 frame hex: {vp8_frame.hex()}")
    print()
    
    # Output as Python bytes literal
    hex_str = ", ".join(f"0x{b:02x}" for b in webm_data)
    print(f"MOCK_WEBM_BYTES = bytes([")
    # Print in rows of 16
    for i in range(0, len(webm_data), 16):
        chunk = webm_data[i:i+16]
        row = ", ".join(f"0x{b:02x}" for b in chunk)
        print(f"    {row},")
    print(f"])")
    print(f"# Total: {len(webm_data)} bytes")
    
    # Also save to file for testing
    with open("test_minimal.webm", "wb") as f:
        f.write(webm_data)
    print(f"\nSaved to test_minimal.webm")
    
    # Base64 for easy embedding
    b64 = base64.b64encode(webm_data).decode()
    print(f"\nBase64: {b64}")
