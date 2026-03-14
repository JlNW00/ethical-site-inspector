"""Check existing audits for validation."""
import json
import urllib.request

resp = urllib.request.urlopen("http://localhost:8000/api/audits")
audits = json.loads(resp.read())
for a in audits:
    vid = a.get("video_urls")
    vid_count = len(vid) if vid else 0
    print(f"  {a['id']} | status={a['status']} | mode={a['mode']} | video_urls_count={vid_count}")

print(f"\nTotal audits: {len(audits)}")

# Check for any with video_urls
with_videos = [a for a in audits if a.get("video_urls")]
print(f"Audits with video URLs: {len(with_videos)}")
if with_videos:
    print(f"  First with video: {with_videos[0]['id']}")
    print(f"  Video keys: {list(with_videos[0]['video_urls'].keys())[:5]}")
