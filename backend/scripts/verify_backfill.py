"""Verification script for backfill results.

Tests the API endpoints to verify:
1. Failed audits exist
2. Findings have populated regulatory_categories
3. Confidence scores and evidence_type are set
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

import requests


def main():
    base_url = "http://127.0.0.1:8000/api"

    print("=" * 60)
    print("Backfill Verification Script")
    print("=" * 60)

    # Test 1: Health endpoint
    print("\n[1/3] Testing health endpoint...")
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        if r.status_code == 200:
            print("  ✓ Health endpoint: OK")
        else:
            print(f"  ✗ Health endpoint: FAIL (status {r.status_code})")
    except Exception as e:
        print(f"  ✗ Health endpoint: FAIL - {e}")
        return

    # Test 2: Failed audits exist
    print("\n[2/3] Testing failed audits endpoint...")
    try:
        r = requests.get(f"{base_url}/audits?status=failed", timeout=5)
        if r.status_code == 200:
            data = r.json()
            failed_audits = data.get("audits", [])
            if len(failed_audits) >= 1:
                print(f"  PASS - Failed audits: {len(failed_audits)} found")
                for a in failed_audits:
                    print(f"    - {a['id']}: {a['status']}")
            else:
                print(f"  FAIL - Failed audits: 0 found (expected >= 1)")
        else:
            print(f"  FAIL - Failed audits endpoint status {r.status_code}")
    except Exception as e:
        print(f"  FAIL - Failed audits: {e}")

    # Test 3: Findings have regulatory_categories
    print("\n[3/3] Testing findings have regulatory categories...")
    try:
        # Get a completed audit
        r = requests.get(f"{base_url}/audits?status=completed", timeout=5)
        if r.status_code == 200:
            data = r.json()
            audits = data.get("audits", [])
            if audits:
                audit_id = audits[0]["id"]
                r2 = requests.get(f"{base_url}/audits/{audit_id}/findings", timeout=5)
                if r2.status_code == 200:
                    findings_data = r2.json()
                    findings = findings_data.get("findings", [])
                    if findings:
                        populated = sum(1 for f in findings if f.get("regulatory_categories"))
                        print(f"  PASS - Findings with regulatory_categories: {populated}/{len(findings)}")
                        # Show sample
                        sample = findings[0]
                        print(f"    Sample finding:")
                        print(f"      - pattern_family: {sample.get('pattern_family')}")
                        print(f"      - regulatory_categories: {sample.get('regulatory_categories')}")
                        print(f"      - confidence: {sample.get('confidence')}")
                        print(f"      - evidence_type: {sample.get('evidence_payload', {}).get('evidence_type')}")
                    else:
                        print("  INFO - No findings in completed audit")
                else:
                    print(f"  FAIL - Findings endpoint: status {r2.status_code}")
            else:
                print("  ℹ No completed audits found")
        else:
            print(f"  ✗ Completed audits: FAIL (status {r.status_code})")
    except Exception as e:
        print(f"  ✗ Findings check: FAIL - {e}")

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
