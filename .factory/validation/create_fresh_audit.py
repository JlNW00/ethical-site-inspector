"""Create a fresh mock audit for validation testing."""
import urllib.request
import json

data = json.dumps({
    "target_url": "https://example.com",
    "selected_scenarios": ["cookie_consent", "checkout_flow"],
    "selected_personas": ["privacy_sensitive", "cost_sensitive"]
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
