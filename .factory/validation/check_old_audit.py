"""Check an old audit without video URLs."""
import json
import urllib.request

# Old mock audit
audit_id = "48fcd4cc-a0a4-454f-8444-4b3b302dd595"
resp = urllib.request.urlopen(f"http://localhost:8000/api/audits/{audit_id}")
audit = json.loads(resp.read())
print(f"ID: {audit['id']}")
print(f"Status: {audit['status']}")
print(f"Mode: {audit['mode']}")
print(f"Video URLs: {audit.get('video_urls')}")
print(f"Trust Score: {audit.get('trust_score')}")
