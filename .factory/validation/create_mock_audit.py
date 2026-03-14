"""Create a mock audit and wait for it to complete with video URLs."""
import json
import time
import urllib.request

# Create audit
data = json.dumps({
    "target_url": "https://example.com"
}).encode()

req = urllib.request.Request(
    "http://localhost:8000/api/audits",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
audit_id = result["id"]
print(f"Created audit: {audit_id}")
print(f"Status: {result['status']}")

# Poll until completed (max 90 seconds)
for i in range(60):
    time.sleep(1.5)
    resp = urllib.request.urlopen(f"http://localhost:8000/api/audits/{audit_id}")
    audit = json.loads(resp.read())
    status = audit["status"]
    if status in ("completed", "failed"):
        print(f"\nFinal status: {status}")
        print(f"Video URLs: {audit.get('video_urls')}")
        print(f"Trust score: {audit.get('trust_score')}")
        print(f"Mode: {audit.get('mode')}")
        
        if audit.get("video_urls"):
            print(f"\nVideo URL count: {len(audit['video_urls'])}")
            for key, url in list(audit["video_urls"].items())[:3]:
                print(f"  {key}: {url}")
        else:
            print("\nWARNING: No video URLs!")
        
        # Print events that mention video
        events = audit.get("events", [])
        video_events = [e for e in events if "video" in e.get("message", "").lower() or e.get("phase") == "video"]
        print(f"\nVideo-related events: {len(video_events)}")
        for e in video_events[:5]:
            print(f"  [{e['phase']}] {e['message']}")
        
        break
    if i % 5 == 0:
        print(f"  ... {status} (poll {i})")
else:
    print("TIMEOUT waiting for audit to complete")

# Save audit ID for subagents
with open("C:/EthicalSiteInspector/.factory/validation/test_audit_id.txt", "w") as f:
    f.write(audit_id)
print(f"\nAudit ID saved to test_audit_id.txt: {audit_id}")
