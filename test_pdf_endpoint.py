"""Quick test for PDF endpoint."""
import requests

resp = requests.get('http://127.0.0.1:8000/api/audits')
audits = resp.json()
print(f"Found {len(audits)} audits")

for audit in audits:
    if audit.get('status') == 'completed' and audit.get('report_path'):
        audit_id = audit['id']
        print(f"\nTesting PDF for audit: {audit_id}")
        pdf_resp = requests.get(f'http://127.0.0.1:8000/api/audits/{audit_id}/report/pdf')
        print(f"Status: {pdf_resp.status_code}")
        print(f"Content-Type: {pdf_resp.headers.get('content-type', 'N/A')}")
        print(f"Size: {len(pdf_resp.content)} bytes")
        print(f"Starts with %PDF: {pdf_resp.content[:4] == b'%PDF'}")
        break
else:
    print("No completed audits with report_path found")
