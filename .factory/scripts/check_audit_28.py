"""Check the audit with 28 findings."""
import json
import urllib.request

resp = urllib.request.urlopen("http://127.0.0.1:8000/api/audits/6af01314-92fe-45f4-bc3d-07e07c535898/findings")
data = json.loads(resp.read())
findings = data.get("findings", [])

print(f"Total findings: {len(findings)}")
for i, f in enumerate(findings[:5]):
    pf = f.get("pattern_family", "?")
    rc = f.get("regulatory_categories", [])
    conf = f.get("confidence", 0)
    supp = f.get("suppressed", False)
    ep = f.get("evidence_payload", {})
    sl = ep.get("source_label", "?")
    et = ep.get("evidence_type", "?")
    print(f"  [{i}] pf={pf} reg={rc} conf={conf} supp={supp} sl={sl} et={et}")
