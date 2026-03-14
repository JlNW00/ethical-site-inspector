"""Check pattern families and regulatory categories in existing findings."""
import json
import urllib.request

data = json.load(open(r"C:\EthicalSiteInspector\data\audits_list.json"))
pattern_families = set()
all_findings_info = []

for a in data:
    if a["status"] != "completed":
        continue
    aid = a["id"]
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:8000/api/audits/{aid}/findings")
        fd = json.loads(resp.read())
        for f in fd.get("findings", []):
            pf = f.get("pattern_family", "?")
            rc = f.get("regulatory_categories", [])
            conf = f.get("confidence", 0)
            supp = f.get("suppressed", False)
            pattern_families.add(pf)
            all_findings_info.append({
                "audit": aid[:8],
                "pattern_family": pf,
                "regulatory_categories": rc,
                "confidence": conf,
                "suppressed": supp,
            })
    except Exception as e:
        print(f"Error for {aid[:8]}: {e}")

print(f"Total findings analyzed: {len(all_findings_info)}")
print(f"Pattern families found: {sorted(pattern_families)}")
print(f"Findings with regulatory_categories: {sum(1 for f in all_findings_info if f['regulatory_categories'])}")
print(f"Findings with suppressed=True: {sum(1 for f in all_findings_info if f['suppressed'])}")

# Show sample
for f in all_findings_info[:5]:
    print(f"  {f['audit']} pf={f['pattern_family']} reg={f['regulatory_categories']} conf={f['confidence']} supp={f['suppressed']}")
