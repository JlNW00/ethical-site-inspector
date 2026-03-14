"""Create a mock audit for video testing validation."""
import json
import urllib.request

data = json.dumps({
    "target_url": "https://example.com",
    "mode": "mock"
}).encode()

req = urllib.request.Request(
    "http://localhost:8000/api/audits",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f"Audit ID: {result['id']}")
print(f"Status: {result['status']}")
print(json.dumps(result, indent=2))
