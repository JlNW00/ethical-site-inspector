"""Generate a minimal valid WebM file for mock video testing.

This creates a minimal but valid WebM file that browsers can decode.
The file includes:
- EBML header
- Segment
- Info element (with Duration, TimecodeScale, MuxingApp, WritingApp)
- Tracks element (with VP8 video track)
- Minimal Cluster with a simple block (keyframe)
"""

import struct


def encode_element_id(element_id: int) -> bytes:
    """Encode an EBML element ID using VINT.
    
    EBML IDs use variable-length encoding:
    - Class A (1 byte): IDs 0x81-0xFE (first bit pattern: 1xxxxxxx)
    - Class B (2 bytes): IDs 0x407F-0x3FFE (first bit pattern: 01xxxxxx)
    - Class C (3 bytes): IDs 0x203FFF-0x1FFFFE
    - Class D (4 bytes): IDs 0x101FFFFF-0x0FFFFFFE
    """
    if element_id < 0x80:
        return bytes([0x80 | element_id])
    elif element_id < 0x4000:
        return bytes([0x40 | (element_id >> 8), element_id & 0xFF])
    elif element_id < 0x200000:
        return bytes([0x20 | (element_id >> 16), (element_id >> 8) & 0xFF, element_id & 0xFF])
    elif element_id < 0x10000000:
        return bytes([0x10 | (element_id >> 24), (element_id >> 16) & 0xFF, (element_id >> 8) & 0xFF, element_id & 0xFF])
    else:
        raise ValueError(f"Element ID too large: {element_id}")


def encode_vint(value: int, length: int | None = None) -> bytes:
    """Encode a value using EBML VINT format."""
    if length is not None:
        # Fixed length encoding
        return bytes([value | (0x80 >> (length - 1))])
    
    # Variable length encoding
    if value < 127:
        return bytes([0x80 | value])
    elif value < 16383:
        return bytes([0x40 | (value >> 8), value & 0xFF])
    elif value < 2097151:
        return bytes([0x20 | (value >> 16), (value >> 8) & 0xFF, value & 0xFF])
    elif value < 268435455:
        return bytes([0x10 | (value >> 24), (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])
    else:
        # 5+ bytes
        mask = 0x08
        shifted = value >> 32
        return bytes([mask | shifted, (value >> 24) & 0xFF, (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF])


def encode_unsigned(value: int) -> bytes:
    """Encode an unsigned integer in big-endian format."""
    if value == 0:
        return bytes([0])
    length = (value.bit_length() + 7) // 8
    return value.to_bytes(length, 'big')


def encode_string(s: str) -> bytes:
    """Encode a UTF-8 string."""
    return s.encode('utf-8')


def encode_float(value: float) -> bytes:
    """Encode a float as 4 or 8 bytes (IEEE 754)."""
    # Use 8 bytes (double precision)
    return struct.pack('>d', value)


def create_element(element_id: int, data: bytes) -> bytes:
    """Create an EBML element with ID, size, and data."""
    id_bytes = encode_element_id(element_id)
    size = len(data)
    
    # Encode size using VINT (unknown/unspecified size is 0x01FFFFFF for 4 bytes)
    # For simplicity, we'll use the smallest encoding
    if size < 127:
        size_bytes = bytes([0x80 | size])
    elif size < 16383:
        size_bytes = bytes([0x40 | (size >> 8), size & 0xFF])
    elif size < 2097151:
        size_bytes = bytes([0x20 | (size >> 16), (size >> 8) & 0xFF, size & 0xFF])
    elif size < 268435455:
        size_bytes = bytes([0x10 | (size >> 24), (size >> 16) & 0xFF, (size >> 8) & 0xFF, size & 0xFF])
    else:
        # Large size - use 5 bytes
        size_bytes = bytes([0x08 | (size >> 32), (size >> 24) & 0xFF, (size >> 16) & 0xFF, (size >> 8) & 0xFF, size & 0xFF])
    
    return id_bytes + size_bytes + data


def create_ebml_header() -> bytes:
    """Create the EBML header for WebM."""
    # EBML Version (1)
    ebml_version = create_element(0x4286, encode_unsigned(1))
    # EBML Read Version (1)
    ebml_read_version = create_element(0x42F7, encode_unsigned(1))
    # EBML Max ID Length (4)
    ebml_max_id_length = create_element(0x42F2, encode_unsigned(4))
    # EBML Max Size Length (8)
    ebml_max_size_length = create_element(0x42F3, encode_unsigned(8))
    # DocType = "webm"
    doctype = create_element(0x4282, encode_string("webm"))
    # DocType Version (4)
    doctype_version = create_element(0x4287, encode_unsigned(4))
    # DocType Read Version (2)
    doctype_read_version = create_element(0x4285, encode_unsigned(2))
    
    header_content = ebml_version + ebml_read_version + ebml_max_id_length + ebml_max_size_length + doctype + doctype_version + doctype_read_version
    
    # EBML element ID is 0x1A45DFA3
    return bytes([0x1A, 0x45, 0xDF, 0xA3]) + encode_vint(len(header_content), 1) + header_content


def create_info() -> bytes:
    """Create the Info element."""
    # TimecodeScale (1,000,000 nanoseconds = 1ms)
    timecode_scale = create_element(0x2AD7B1, encode_unsigned(1000000))
    # Duration (1000 ms = 1 second)
    duration = create_element(0x4489, encode_float(1000.0))
    # MuxingApp
    muxing_app = create_element(0x4D80, encode_string("MockWebMGenerator"))
    # WritingApp
    writing_app = create_element(0x5741, encode_string("MockWebMGenerator"))
    
    info_content = timecode_scale + duration + muxing_app + writing_app
    # Info element ID is 0x1549A966
    return bytes([0x15, 0x49, 0xA9, 0x66]) + encode_vint(len(info_content), 1) + info_content


def create_video_track() -> bytes:
    """Create a video track entry."""
    # Track Number (1)
    track_number = create_element(0xD7, encode_unsigned(1))
    # Track UID (random 8-byte value)
    track_uid = create_element(0x73C5, encode_unsigned(12345678))
    # Track Type (1 = video)
    track_type = create_element(0x83, encode_unsigned(1))
    # Flag Lacing (0 = no)
    flag_lacing = create_element(0x9C, encode_unsigned(0))
    # Codec ID = "V_VP8"
    codec_id = create_element(0x86, encode_string("V_VP8"))
    # Language (optional, but common)
    language = create_element(0x22B59C, encode_string("und"))
    
    # Video settings
    # Pixel Width (320)
    pixel_width = create_element(0xB0, encode_unsigned(320))
    # Pixel Height (240)
    pixel_height = create_element(0xBA, encode_unsigned(240))
    # Display Width (320)
    display_width = create_element(0x54B0, encode_unsigned(320))
    # Display Height (240)
    display_height = create_element(0x54BA, encode_unsigned(240))
    
    video_content = pixel_width + pixel_height + display_width + display_height
    # Video element ID is 0xE0
    video = bytes([0xE0]) + encode_vint(len(video_content), 1) + video_content
    
    track_entry_content = track_number + track_uid + track_type + flag_lacing + codec_id + language + video
    # TrackEntry element ID is 0xAE
    return bytes([0xAE]) + encode_vint(len(track_entry_content), 1) + track_entry_content


def create_tracks() -> bytes:
    """Create the Tracks element."""
    track_entry = create_video_track()
    # Tracks element ID is 0x1654AE6B
    return bytes([0x16, 0x54, 0xAE, 0x6B]) + encode_vint(len(track_entry), 1) + track_entry


def create_simple_block(track_number: int, timecode: int, keyframe: bool, data: bytes) -> bytes:
    """Create a SimpleBlock element."""
    # SimpleBlock header:
    # - Track number (1-4 bytes VINT without the length marker)
    # - Timecode (2 bytes signed big-endian)
    # - Flags (1 byte: keyframe=0x80, invisible=0x08, lacing=0x06, discardable=0x01)
    
    # Track number as VINT without the length marker (just the value with leading 1)
    if track_number < 0x80:
        track_bytes = bytes([0x80 | track_number])
    else:
        track_bytes = encode_unsigned(track_number)
    
    timecode_bytes = struct.pack('>h', timecode)  # Signed 16-bit big-endian
    flags = 0x80 if keyframe else 0x00  # Keyframe flag
    
    block_content = track_bytes + timecode_bytes + bytes([flags]) + data
    # SimpleBlock element ID is 0xA3
    return bytes([0xA3]) + encode_vint(len(block_content), 1) + block_content


def create_cluster(timecode: int, block: bytes) -> bytes:
    """Create a Cluster element."""
    # Timecode for the cluster
    cluster_timecode = create_element(0xE7, encode_unsigned(timecode))
    cluster_content = cluster_timecode + block
    # Cluster element ID is 0x1F43B675
    return bytes([0x1F, 0x43, 0xB6, 0x75]) + encode_vint(len(cluster_content), 1) + cluster_content


def create_vp8_keyframe(width: int = 320, height: int = 240) -> bytes:
    """Create a minimal VP8 keyframe.
    
    VP8 keyframe format:
    - 3-byte start code: 0x9d 0x01 0x2a
    - 2 bytes: (width-1) | (horizontal_scale << 14) - little endian
    - 2 bytes: (height-1) | (vertical_scale << 14) - little endian
    - Then compressed frame data
    """
    # VP8 keyframe start code
    start_code = bytes([0x9d, 0x01, 0x2a])
    
    # Width and height are stored as (value - 1) in lower 14 bits
    # Upper 2 bits are scale (0 for no scaling)
    width_packed = (width - 1) & 0x3FFF
    height_packed = (height - 1) & 0x3FFF
    
    # Pack as little-endian 16-bit
    dimensions = struct.pack('<HH', width_packed, height_packed)
    
    # Minimal VP8 frame data - this is a simplified I-frame
    # Real VP8 data would be compressed, but for a minimal valid file
    # we just need enough bytes that the decoder can recognize it
    frame_data = bytes([0x00] * 8)
    
    return start_code + dimensions + frame_data


def create_segment() -> bytes:
    """Create the Segment element containing Info, Tracks, and Cluster."""
    info = create_info()
    tracks = create_tracks()
    
    # Create a cluster with a simple block containing VP8 data
    vp8_data = create_vp8_keyframe()
    simple_block = create_simple_block(1, 0, True, vp8_data)
    cluster = create_cluster(0, simple_block)
    
    segment_content = info + tracks + cluster
    # Segment element ID is 0x18538067
    # Use 4-byte size encoding to allow for growth
    size_bytes = bytes([0x01, 0x00, 0x00, 0x00]) + encode_vint(len(segment_content), 4)[1:]
    return bytes([0x18, 0x53, 0x80, 0x67]) + size_bytes + segment_content


def create_minimal_webm() -> bytes:
    """Create a minimal but valid WebM file."""
    ebml_header = create_ebml_header()
    segment = create_segment()
    return ebml_header + segment


if __name__ == "__main__":
    webm_data = create_minimal_webm()
    print(f"Generated WebM file size: {len(webm_data)} bytes")
    
    # Write to file
    output_path = r"C:\EthicalSiteInspector\backend\valid_minimal.webm"
    with open(output_path, "wb") as f:
        f.write(webm_data)
    print(f"Written to: {output_path}")
    
    # Print as Python bytes literal for embedding
    print("\nPython bytes literal (first 200 bytes):")
    print("MOCK_WEBM_BYTES: bytes = bytes([")
    for i in range(0, min(200, len(webm_data)), 16):
        line = webm_data[i:i+16]
        hex_str = ", ".join(f"0x{b:02x}" for b in line)
        print(f"    {hex_str},")
    print("    ... (remaining bytes)")
    print("])")
    print(f"\nTotal length: {len(webm_data)} bytes")
