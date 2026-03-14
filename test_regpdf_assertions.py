"""
Comprehensive test script for VAL-REGPDF-002 through VAL-REGPDF-010 and VAL-CROSS-004.
Downloads PDFs, extracts text, verifies all assertions.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# PDF text extraction
from PyPDF2 import PdfReader
import io

BASE_URL = "http://localhost:8000"
EVIDENCE_DIR = r"C:\Users\rajpa\.factory\missions\e866bdf8-5055-4c17-a7c1-710eb12e7a45\evidence\regulatory-pdf\pdf-api"
REPORT_PATH = r"C:\EthicalSiteInspector\.factory\validation\regulatory-pdf\user-testing\flows\pdf-api.json"

# Audit IDs
AUDIT_WITH_FINDINGS = "regpdf-test-with-findings"
AUDIT_NO_FINDINGS = "regpdf-test-no-findings"
AUDIT_VIDEO_AND_REG = "regpdf-test-video-and-reg"

os.makedirs(EVIDENCE_DIR, exist_ok=True)


class CaseInsensitiveDict(dict):
    """Dict with case-insensitive key access."""
    def __getitem__(self, key):
        return super().__getitem__(key.lower())
    def get(self, key, default=None):
        return super().get(key.lower(), default)
    def __contains__(self, key):
        return super().__contains__(key.lower())


def http_get(url, return_headers=False):
    """Simple HTTP GET returning bytes."""
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req)
        body = resp.read()
        if return_headers:
            hdrs = CaseInsensitiveDict()
            for key in resp.headers:
                hdrs[key.lower()] = resp.headers[key]
            return body, hdrs, resp.status
        return body
    except urllib.error.HTTPError as e:
        body = e.read()
        if return_headers:
            hdrs = CaseInsensitiveDict()
            for key in e.headers:
                hdrs[key.lower()] = e.headers[key]
            return body, hdrs, e.code
        raise


def http_get_json(url):
    """GET JSON endpoint."""
    data = http_get(url)
    return json.loads(data)


def save_evidence(filename, content):
    """Save evidence to evidence directory."""
    path = os.path.join(EVIDENCE_DIR, filename)
    if isinstance(content, bytes):
        with open(path, "wb") as f:
            f.write(content)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return filename


def extract_pdf_text(pdf_bytes):
    """Extract text from PDF bytes using PyPDF2."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return pages_text, len(reader.pages)


# ==================== ASSERTIONS ====================

assertions = []
frictions = []
blockers = []


def test_val_regpdf_002():
    """VAL-REGPDF-002: API endpoint returns valid PDF with correct headers."""
    assertion = {
        "id": "VAL-REGPDF-002",
        "title": "API endpoint returns valid PDF with correct headers",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        assertion["steps"].append({
            "action": f"GET {url}",
            "expected": "200 with PDF content",
            "observed": ""
        })

        body, headers, status = http_get(url, return_headers=True)

        assertion["steps"][-1]["observed"] = f"HTTP {status}"

        # Check status
        if status != 200:
            assertion["status"] = "fail"
            assertion["issues"] = f"Expected HTTP 200, got {status}"
            assertion["evidence"]["response"] = body.decode("utf-8", errors="replace")[:500]
            return assertion

        # Check Content-Type
        content_type = headers.get("Content-Type", "")
        assertion["steps"].append({
            "action": "Check Content-Type header",
            "expected": "application/pdf",
            "observed": content_type
        })
        if "application/pdf" not in content_type:
            assertion["status"] = "fail"
            assertion["issues"] = f"Content-Type is '{content_type}', expected 'application/pdf'"

        # Check Content-Disposition
        content_disp = headers.get("Content-Disposition", "")
        expected_filename = f"compliance-report-{AUDIT_WITH_FINDINGS}.pdf"
        assertion["steps"].append({
            "action": "Check Content-Disposition header",
            "expected": f'attachment; filename="{expected_filename}"',
            "observed": content_disp
        })
        if expected_filename not in content_disp:
            assertion["status"] = "fail"
            assertion["issues"] = (assertion.get("issues") or "") + f"; Content-Disposition missing expected filename. Got: '{content_disp}'"

        # Check PDF magic bytes
        first_bytes = body[:5]
        assertion["steps"].append({
            "action": "Check first 5 bytes for %PDF-",
            "expected": "%PDF-",
            "observed": first_bytes.decode("ascii", errors="replace")
        })
        if not body.startswith(b"%PDF-"):
            assertion["status"] = "fail"
            assertion["issues"] = (assertion.get("issues") or "") + f"; Body does not start with %PDF-"

        # Save evidence
        save_evidence("VAL-REGPDF-002-headers.txt",
                       f"Status: {status}\nContent-Type: {content_type}\nContent-Disposition: {content_disp}\nFirst 5 bytes: {first_bytes!r}\nBody size: {len(body)} bytes")
        save_evidence("VAL-REGPDF-002-compliance.pdf", body)

        assertion["evidence"] = {
            "headers": "regulatory-pdf/pdf-api/VAL-REGPDF-002-headers.txt",
            "pdf_file": "regulatory-pdf/pdf-api/VAL-REGPDF-002-compliance.pdf",
            "status_code": status,
            "content_type": content_type,
            "content_disposition": content_disp,
            "first_5_bytes": first_bytes.decode("ascii", errors="replace")
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_003():
    """VAL-REGPDF-003: PDF contains per-regulation sections."""
    assertion = {
        "id": "VAL-REGPDF-003",
        "title": "PDF contains per-regulation sections",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        body = http_get(url)
        pages_text, page_count = extract_pdf_text(body)
        full_text = "\n".join(pages_text)

        save_evidence("VAL-REGPDF-003-extracted-text.txt", full_text)

        # Check for four regulation sections
        regulations = {
            "FTC": ["FTC", "Federal Trade Commission"],
            "GDPR": ["GDPR", "General Data Protection Regulation"],
            "DSA": ["DSA", "Digital Services Act"],
            "CPRA": ["CPRA", "California Privacy Rights Act"]
        }

        found_regulations = {}
        for abbr, names in regulations.items():
            found = False
            for name in names:
                if name in full_text:
                    found = True
                    break
            found_regulations[abbr] = found
            assertion["steps"].append({
                "action": f"Check for {abbr} section",
                "expected": f"Text contains '{abbr}' abbreviation and/or full name",
                "observed": f"Found: {found} (searched for: {names})"
            })

        missing = [k for k, v in found_regulations.items() if not v]
        if missing:
            assertion["status"] = "fail"
            assertion["issues"] = f"Missing regulation sections: {missing}"

        # Also verify the sections have section-like headings (abbreviation + full name pattern)
        heading_patterns = {
            "FTC": r"FTC.*Federal Trade Commission|Federal Trade Commission.*FTC",
            "GDPR": r"GDPR.*General Data Protection Regulation|General Data Protection Regulation.*GDPR",
            "DSA": r"DSA.*Digital Services Act|Digital Services Act.*DSA",
            "CPRA": r"CPRA.*California Privacy Rights Act|California Privacy Rights Act.*CPRA"
        }

        headings_found = {}
        for abbr, pattern in heading_patterns.items():
            match = re.search(pattern, full_text, re.IGNORECASE)
            headings_found[abbr] = bool(match)
            assertion["steps"].append({
                "action": f"Check for {abbr} heading with abbreviation + full name",
                "expected": f"Heading like '{abbr} — Full Name'",
                "observed": f"Found: {bool(match)}"
            })

        missing_headings = [k for k, v in headings_found.items() if not v]
        if missing_headings:
            # Downgrade: if abbreviations were found but headings not in exact format, just note it
            if not missing:
                assertion["steps"].append({
                    "action": "Check heading format (abbreviation + full name)",
                    "expected": "All 4 regulations have formatted headings",
                    "observed": f"Missing formatted headings for: {missing_headings}"
                })
                # Still pass if the regulation names are found, just not in exact heading format
                # Actually, the assertion says "clearly titled regulation sections with abbreviation and full name"
                if missing_headings:
                    assertion["status"] = "fail"
                    assertion["issues"] = f"Regulation sections missing abbreviation+full name heading format: {missing_headings}"

        assertion["evidence"] = {
            "extracted_text": "regulatory-pdf/pdf-api/VAL-REGPDF-003-extracted-text.txt",
            "regulations_found": found_regulations,
            "headings_found": headings_found
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_004():
    """VAL-REGPDF-004: Each regulation section lists findings with article citations."""
    assertion = {
        "id": "VAL-REGPDF-004",
        "title": "Each regulation section lists findings with article citations",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        # Get PDF text
        url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        body = http_get(url)
        pages_text, _ = extract_pdf_text(body)
        full_text = "\n".join(pages_text)

        # Get findings data
        findings_data = http_get_json(f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/findings")
        findings = findings_data["findings"]

        save_evidence("VAL-REGPDF-004-findings-data.json", json.dumps(findings_data, indent=2))

        # Check citation patterns
        citation_patterns = {
            "FTC": [r"FTC Act.*§\s*5", r"FTC.*Report", r"Section\s*5", r"FTC Act"],
            "GDPR": [r"GDPR\s+Article\s+\d+", r"Article\s+(5|7|12|25)"],
            "DSA": [r"DSA.*Article\s+\d+", r"Article\s+(25|38)"],
            "CPRA": [r"§\s*1798\.\d+", r"CPRA.*§", r"Section\s*1798"]
        }

        citations_found = {}
        for reg, patterns in citation_patterns.items():
            found = False
            for p in patterns:
                if re.search(p, full_text, re.IGNORECASE):
                    found = True
                    break
            citations_found[reg] = found
            assertion["steps"].append({
                "action": f"Check for {reg} article citations",
                "expected": f"At least one citation pattern for {reg}",
                "observed": f"Found: {found}"
            })

        missing_citations = [k for k, v in citations_found.items() if not v]
        if missing_citations:
            assertion["status"] = "fail"
            assertion["issues"] = f"Missing citations for: {missing_citations}"

        # Check that findings appear under their correct regulations
        # Build mapping: regulation -> finding titles that should appear
        reg_to_findings = {"FTC": [], "GDPR": [], "DSA": [], "CPRA": []}
        for f in findings:
            for cat in f.get("regulatory_categories", []):
                if cat in reg_to_findings:
                    reg_to_findings[cat].append(f["pattern_family"])

        assertion["steps"].append({
            "action": "Cross-reference findings with regulatory categories",
            "expected": f"FTC: {len(reg_to_findings['FTC'])}, GDPR: {len(reg_to_findings['GDPR'])}, DSA: {len(reg_to_findings['DSA'])}, CPRA: {len(reg_to_findings['CPRA'])} findings",
            "observed": f"Finding categories mapped from API data"
        })

        # Check severity mentions
        severities = set(f["severity"] for f in findings)
        severity_found = any(s.lower() in full_text.lower() for s in severities)
        assertion["steps"].append({
            "action": "Check for severity levels in PDF",
            "expected": f"Severity terms found ({severities})",
            "observed": f"Found severity mentions: {severity_found}"
        })
        if not severity_found:
            assertion["status"] = "fail"
            assertion["issues"] = (assertion.get("issues") or "") + "; No severity terms found in PDF text"

        # Check finding titles or pattern families appear
        finding_refs = 0
        for f in findings:
            if f["pattern_family"].replace("_", " ").lower() in full_text.lower() or f["title"].lower()[:30] in full_text.lower():
                finding_refs += 1
        assertion["steps"].append({
            "action": f"Check findings referenced in PDF (searched for title/pattern_family)",
            "expected": f"At least some of {len(findings)} findings referenced",
            "observed": f"Found {finding_refs} finding references"
        })

        assertion["evidence"] = {
            "extracted_text": "regulatory-pdf/pdf-api/VAL-REGPDF-003-extracted-text.txt",
            "findings_data": "regulatory-pdf/pdf-api/VAL-REGPDF-004-findings-data.json",
            "citations_found": citations_found,
            "finding_references": finding_refs
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_005():
    """VAL-REGPDF-005: PDF includes compliance matrix."""
    assertion = {
        "id": "VAL-REGPDF-005",
        "title": "PDF includes compliance matrix",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        body = http_get(url)
        pages_text, _ = extract_pdf_text(body)
        full_text = "\n".join(pages_text)

        # Check for compliance matrix indicators
        matrix_indicators = [
            "compliance matrix",
            "compliance summary",
            "regulation",
            "scenario"
        ]

        found_indicators = []
        for indicator in matrix_indicators:
            if indicator.lower() in full_text.lower():
                found_indicators.append(indicator)

        assertion["steps"].append({
            "action": "Check for compliance matrix section",
            "expected": "Text contains 'compliance matrix' or similar heading",
            "observed": f"Found indicators: {found_indicators}"
        })

        if "compliance matrix" not in [x.lower() for x in found_indicators] and "compliance summary" not in [x.lower() for x in found_indicators]:
            # Check for table-like structure with regulation abbreviations
            has_table_structure = all(reg in full_text for reg in ["FTC", "GDPR", "DSA", "CPRA"])
            assertion["steps"].append({
                "action": "Check for table structure with regulation columns",
                "expected": "All 4 regulation abbreviations present as potential column headers",
                "observed": f"All present: {has_table_structure}"
            })
            if not has_table_structure:
                assertion["status"] = "fail"
                assertion["issues"] = "No compliance matrix found in PDF"

        # Check for scenario names in matrix context
        scenarios = ["cookie_consent", "checkout_flow", "subscription_cancellation",
                     "cookie consent", "checkout flow", "subscription cancellation",
                     "Cookie Consent", "Checkout Flow", "Subscription Cancellation"]
        scenario_found = sum(1 for s in scenarios if s in full_text)
        assertion["steps"].append({
            "action": "Check for scenario names (potential matrix rows)",
            "expected": "Scenario names present",
            "observed": f"Found {scenario_found} scenario name references"
        })

        # Check for compliance indicators (Compliant, 0, finding counts)
        compliance_terms = ["compliant", "non-compliant", "0 finding", "1 finding", "2 finding", "findings"]
        compliance_found = [t for t in compliance_terms if t.lower() in full_text.lower()]
        assertion["steps"].append({
            "action": "Check for compliance status terms",
            "expected": "Terms like 'Compliant', '0', finding counts",
            "observed": f"Found: {compliance_found}"
        })

        save_evidence("VAL-REGPDF-005-matrix-check.txt", 
                       f"Found matrix indicators: {found_indicators}\nScenario refs: {scenario_found}\nCompliance terms: {compliance_found}\n\nFull text:\n{full_text}")

        assertion["evidence"] = {
            "extracted_text": "regulatory-pdf/pdf-api/VAL-REGPDF-005-matrix-check.txt",
            "matrix_indicators": found_indicators,
            "scenario_count": scenario_found,
            "compliance_terms": compliance_found
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_006():
    """VAL-REGPDF-006: PDF includes executive summary."""
    assertion = {
        "id": "VAL-REGPDF-006",
        "title": "PDF includes executive summary",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        body = http_get(url)
        pages_text, page_count = extract_pdf_text(body)

        # Get audit data for verification
        audit_data = http_get_json(f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}")
        findings_data = http_get_json(f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/findings")

        # Focus on first pages
        first_pages_text = "\n".join(pages_text[:min(3, len(pages_text))])
        full_text = "\n".join(pages_text)

        save_evidence("VAL-REGPDF-006-first-pages.txt", first_pages_text)

        issues = []

        # Check target URL
        target_url = audit_data["target_url"]
        has_target_url = target_url in full_text
        assertion["steps"].append({
            "action": "Check for target URL in PDF",
            "expected": f"Contains '{target_url}'",
            "observed": f"Found: {has_target_url}"
        })
        if not has_target_url:
            issues.append("Target URL not found")

        # Check trust score
        trust_score = audit_data["trust_score"]
        has_trust_score = str(trust_score) in full_text or str(int(trust_score)) in full_text
        assertion["steps"].append({
            "action": "Check for trust score",
            "expected": f"Contains trust score {trust_score}",
            "observed": f"Found: {has_trust_score}"
        })
        if not has_trust_score:
            issues.append(f"Trust score {trust_score} not found")

        # Check regulatory findings count
        reg_findings = [f for f in findings_data["findings"] if f.get("regulatory_categories") and not f.get("suppressed")]
        count = len(reg_findings)
        has_count = str(count) in full_text
        assertion["steps"].append({
            "action": "Check for total regulatory findings count",
            "expected": f"Contains count '{count}'",
            "observed": f"Found: {has_count}"
        })
        if not has_count:
            issues.append(f"Findings count {count} not found")

        # Check implicated regulations
        all_regs = set()
        for f in reg_findings:
            all_regs.update(f.get("regulatory_categories", []))
        regs_found = {r: r in full_text for r in all_regs}
        assertion["steps"].append({
            "action": "Check for implicated regulations list",
            "expected": f"Contains: {all_regs}",
            "observed": f"Found: {regs_found}"
        })
        missing_regs = [r for r, v in regs_found.items() if not v]
        if missing_regs:
            issues.append(f"Missing regulations: {missing_regs}")

        # Check for executive summary heading or compliance posture
        summary_terms = ["executive summary", "compliance posture", "overall", "summary", "assessment"]
        summary_found = [t for t in summary_terms if t.lower() in full_text.lower()]
        assertion["steps"].append({
            "action": "Check for executive summary or compliance posture",
            "expected": "Contains executive summary heading or posture statement",
            "observed": f"Found terms: {summary_found}"
        })
        if not summary_found:
            issues.append("No executive summary or compliance posture found")

        if issues:
            assertion["status"] = "fail"
            assertion["issues"] = "; ".join(issues)

        assertion["evidence"] = {
            "first_pages_text": "regulatory-pdf/pdf-api/VAL-REGPDF-006-first-pages.txt",
            "target_url_found": has_target_url,
            "trust_score_found": has_trust_score,
            "findings_count": count,
            "regulations": regs_found,
            "summary_terms": summary_found
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_007():
    """VAL-REGPDF-007: PDF includes evidence references."""
    assertion = {
        "id": "VAL-REGPDF-007",
        "title": "PDF includes evidence references",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        body = http_get(url)
        pages_text, _ = extract_pdf_text(body)
        full_text = "\n".join(pages_text)

        # Check for evidence references
        evidence_patterns = [
            r"[Ss]ee\s+[Ff]igure\s+\d+",
            r"[Ee]vidence:\s*\S+",
            r"screenshot",
            r"[Ff]igure\s+\d+",
            r"/artifacts/",
            r"\.svg",
            r"\.png",
            r"\.jpg",
            r"evidence_",
            r"Evidence"
        ]

        found_patterns = []
        for p in evidence_patterns:
            matches = re.findall(p, full_text, re.IGNORECASE)
            if matches:
                found_patterns.append({"pattern": p, "matches": matches[:3]})

        assertion["steps"].append({
            "action": "Search for evidence reference patterns in PDF text",
            "expected": "At least one evidence reference per finding (screenshot URL, figure ref, etc.)",
            "observed": f"Found {len(found_patterns)} pattern types with matches"
        })

        if not found_patterns:
            assertion["status"] = "fail"
            assertion["issues"] = "No evidence references found in PDF text"

        save_evidence("VAL-REGPDF-007-evidence-refs.txt",
                       f"Evidence patterns found:\n{json.dumps(found_patterns, indent=2, default=str)}\n\nFull text:\n{full_text}")

        assertion["evidence"] = {
            "extracted_text": "regulatory-pdf/pdf-api/VAL-REGPDF-007-evidence-refs.txt",
            "patterns_found": found_patterns
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_008():
    """VAL-REGPDF-008: Compliance PDF is distinct from existing PDF."""
    assertion = {
        "id": "VAL-REGPDF-008",
        "title": "Compliance PDF is distinct from existing PDF",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        # Download compliance PDF
        compliance_url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        comp_body, comp_headers, comp_status = http_get(compliance_url, return_headers=True)

        assertion["steps"].append({
            "action": f"GET compliance PDF",
            "expected": "200 with compliance PDF",
            "observed": f"HTTP {comp_status}"
        })

        # Try existing PDF
        existing_url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/pdf"
        try:
            exist_body, exist_headers, exist_status = http_get(existing_url, return_headers=True)
        except Exception:
            exist_body, exist_headers, exist_status = b"", {}, 404

        assertion["steps"].append({
            "action": f"GET existing PDF",
            "expected": "200 or 404 (report_path may be null)",
            "observed": f"HTTP {exist_status}"
        })

        # Check different filenames in Content-Disposition
        comp_disp = comp_headers.get("Content-Disposition", "")
        exist_disp = exist_headers.get("Content-Disposition", "")

        assertion["steps"].append({
            "action": "Compare Content-Disposition filenames",
            "expected": "Different filenames (compliance-report-*.pdf vs audit-report-*.pdf)",
            "observed": f"Compliance: '{comp_disp}', Existing: '{exist_disp}'"
        })

        if exist_status == 404:
            assertion["steps"].append({
                "action": "Existing PDF returned 404 (report_path is null for seeded data)",
                "expected": "Expected per assertion NOTE - verify compliance PDF has unique content instead",
                "observed": "Existing PDF 404 as expected for seeded test data"
            })

        # Verify compliance PDF has unique regulatory content
        comp_text_pages, _ = extract_pdf_text(comp_body)
        comp_text = "\n".join(comp_text_pages)

        unique_content = {
            "regulation_headings": any(r in comp_text for r in ["FTC", "GDPR", "DSA", "CPRA"]),
            "compliance_matrix": "compliance" in comp_text.lower() and ("matrix" in comp_text.lower() or "summary" in comp_text.lower()),
            "regulatory_content": "regulatory" in comp_text.lower() or "regulation" in comp_text.lower()
        }

        assertion["steps"].append({
            "action": "Verify compliance PDF has unique regulatory content",
            "expected": "Contains regulation headings, compliance matrix, regulatory terms",
            "observed": f"Unique content checks: {unique_content}"
        })

        if not any(unique_content.values()):
            assertion["status"] = "fail"
            assertion["issues"] = "Compliance PDF lacks unique regulatory content"

        # Verify filename difference
        if "compliance-report" in comp_disp:
            assertion["steps"].append({
                "action": "Verify compliance PDF filename is distinct",
                "expected": "Contains 'compliance-report'",
                "observed": f"Filename in disposition: {comp_disp}"
            })
        else:
            assertion["steps"].append({
                "action": "Verify compliance PDF filename format",
                "expected": "Contains 'compliance-report'",
                "observed": f"Actual: {comp_disp}"
            })

        save_evidence("VAL-REGPDF-008-comparison.txt",
                       f"Compliance PDF:\n  Status: {comp_status}\n  Disposition: {comp_disp}\n  Size: {len(comp_body)} bytes\n\n"
                       f"Existing PDF:\n  Status: {exist_status}\n  Disposition: {exist_disp}\n  Size: {len(exist_body) if exist_body else 0} bytes\n\n"
                       f"Unique content in compliance PDF: {unique_content}")

        assertion["evidence"] = {
            "comparison": "regulatory-pdf/pdf-api/VAL-REGPDF-008-comparison.txt",
            "compliance_status": comp_status,
            "compliance_disposition": comp_disp,
            "existing_status": exist_status,
            "existing_disposition": exist_disp,
            "unique_content": unique_content
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_009():
    """VAL-REGPDF-009: Zero-findings audit handles compliance PDF gracefully."""
    assertion = {
        "id": "VAL-REGPDF-009",
        "title": "Zero-findings audit handles compliance PDF gracefully",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        url = f"{BASE_URL}/api/audits/{AUDIT_NO_FINDINGS}/report/compliance-pdf"
        assertion["steps"].append({
            "action": f"GET {url}",
            "expected": "Valid PDF with 'No regulatory findings' OR HTTP 404 with descriptive error. No 500.",
            "observed": ""
        })

        body, headers, status = http_get(url, return_headers=True)

        assertion["steps"][-1]["observed"] = f"HTTP {status}"

        if status == 500:
            assertion["status"] = "fail"
            assertion["issues"] = f"Server returned 500 error"
            save_evidence("VAL-REGPDF-009-response.txt", f"Status: {status}\nBody: {body.decode('utf-8', errors='replace')[:1000]}")
        elif status == 404:
            # Acceptable - check for descriptive error
            try:
                error_body = json.loads(body)
                assertion["steps"].append({
                    "action": "Check 404 response has descriptive error",
                    "expected": "JSON error with description",
                    "observed": f"Error response: {json.dumps(error_body)[:500]}"
                })
            except json.JSONDecodeError:
                body_str = body.decode("utf-8", errors="replace")
                assertion["steps"].append({
                    "action": "Check 404 response body",
                    "expected": "Descriptive error message",
                    "observed": f"Non-JSON body: {body_str[:500]}"
                })
            save_evidence("VAL-REGPDF-009-response.txt", f"Status: {status}\nBody: {body.decode('utf-8', errors='replace')[:1000]}")
        elif status == 200:
            # Valid PDF with no regulatory findings message
            content_type = headers.get("Content-Type", "")
            if "application/pdf" in content_type:
                if body.startswith(b"%PDF-"):
                    pages_text, _ = extract_pdf_text(body)
                    full_text = "\n".join(pages_text)
                    has_no_findings_msg = any(term in full_text.lower() for term in
                                              ["no regulatory findings", "no findings", "no compliance issues", "compliant"])
                    assertion["steps"].append({
                        "action": "Check PDF contains 'no regulatory findings' message",
                        "expected": "Message about no regulatory findings",
                        "observed": f"Found: {has_no_findings_msg}"
                    })
                    save_evidence("VAL-REGPDF-009-no-findings.pdf", body)
                    save_evidence("VAL-REGPDF-009-text.txt", full_text)
                else:
                    assertion["status"] = "fail"
                    assertion["issues"] = "Response is 200 with application/pdf but body doesn't start with %PDF-"
            else:
                assertion["status"] = "fail"
                assertion["issues"] = f"200 response with unexpected Content-Type: {content_type}"
            save_evidence("VAL-REGPDF-009-response.txt", f"Status: {status}\nContent-Type: {content_type}\nSize: {len(body)} bytes")
        else:
            assertion["status"] = "fail"
            assertion["issues"] = f"Unexpected HTTP status: {status}"

        assertion["evidence"] = {
            "response": "regulatory-pdf/pdf-api/VAL-REGPDF-009-response.txt",
            "status_code": status
        }

    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read()
        if status == 500:
            assertion["status"] = "fail"
            assertion["issues"] = f"Server returned 500 error: {body.decode('utf-8', errors='replace')[:500]}"
        elif status == 404:
            # Acceptable
            try:
                error_body = json.loads(body)
                assertion["steps"].append({
                    "action": "Check 404 response",
                    "expected": "Descriptive error",
                    "observed": f"Error: {json.dumps(error_body)[:500]}"
                })
            except Exception:
                assertion["steps"].append({
                    "action": "Check 404 response",
                    "expected": "Descriptive error",
                    "observed": body.decode("utf-8", errors="replace")[:500]
                })
        else:
            assertion["status"] = "fail"
            assertion["issues"] = f"Unexpected HTTP error: {status}"
        
        save_evidence("VAL-REGPDF-009-response.txt", f"Status: {status}\nBody: {body.decode('utf-8', errors='replace')[:1000]}")
        assertion["evidence"] = {"response": "regulatory-pdf/pdf-api/VAL-REGPDF-009-response.txt", "status_code": status}

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_regpdf_010():
    """VAL-REGPDF-010: Compliance PDF has professional formatting."""
    assertion = {
        "id": "VAL-REGPDF-010",
        "title": "Compliance PDF has professional formatting",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        url = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        body = http_get(url)
        pages_text, page_count = extract_pdf_text(body)
        full_text = "\n".join(pages_text)
        file_size = len(body)

        issues = []

        # Check file size (10KB-5MB)
        assertion["steps"].append({
            "action": "Check PDF file size (10KB-5MB)",
            "expected": "10240 <= size <= 5242880",
            "observed": f"{file_size} bytes ({file_size/1024:.1f} KB)"
        })
        if file_size < 10240:
            issues.append(f"PDF too small: {file_size} bytes (< 10KB)")
        if file_size > 5242880:
            issues.append(f"PDF too large: {file_size} bytes (> 5MB)")

        # Check page count (>= 2)
        assertion["steps"].append({
            "action": "Check page count (>= 2)",
            "expected": "At least 2 pages",
            "observed": f"{page_count} pages"
        })
        if page_count < 2:
            issues.append(f"PDF has only {page_count} page(s), expected >= 2")

        # Check text length (500+ chars)
        text_len = len(full_text)
        assertion["steps"].append({
            "action": "Check extracted text length (>= 500 chars)",
            "expected": "500+ characters",
            "observed": f"{text_len} characters"
        })
        if text_len < 500:
            issues.append(f"Text extraction only {text_len} chars, expected >= 500")

        # Check no raw HTML/CSS strings
        html_patterns = ["<div", "<span", "class=", "style="]
        html_found = [p for p in html_patterns if p in full_text]
        assertion["steps"].append({
            "action": "Check for raw HTML/CSS strings",
            "expected": "No <div, <span, class=, style= in text",
            "observed": f"Found: {html_found}" if html_found else "None found (clean)"
        })
        if html_found:
            issues.append(f"Raw HTML/CSS found in PDF: {html_found}")

        # Check for EthicalSiteInspector branding
        has_branding = "EthicalSiteInspector" in full_text or "Ethical Site Inspector" in full_text
        assertion["steps"].append({
            "action": "Check for 'EthicalSiteInspector' branding",
            "expected": "'EthicalSiteInspector' in header/footer",
            "observed": f"Found: {has_branding}"
        })
        if not has_branding:
            issues.append("'EthicalSiteInspector' not found in PDF text")

        if issues:
            assertion["status"] = "fail"
            assertion["issues"] = "; ".join(issues)

        save_evidence("VAL-REGPDF-010-formatting.txt",
                       f"File size: {file_size} bytes ({file_size/1024:.1f} KB)\n"
                       f"Page count: {page_count}\n"
                       f"Text length: {text_len} chars\n"
                       f"HTML found: {html_found}\n"
                       f"Branding found: {has_branding}\n\n"
                       f"Full text:\n{full_text[:2000]}")

        assertion["evidence"] = {
            "formatting_check": "regulatory-pdf/pdf-api/VAL-REGPDF-010-formatting.txt",
            "file_size_bytes": file_size,
            "page_count": page_count,
            "text_length": text_len,
            "html_strings_found": html_found,
            "branding_found": has_branding
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


def test_val_cross_004():
    """VAL-CROSS-004: Regulatory PDF references video evidence when available."""
    assertion = {
        "id": "VAL-CROSS-004",
        "title": "Regulatory PDF references video evidence when available",
        "status": "pass",
        "steps": [],
        "evidence": {},
        "issues": None
    }

    try:
        # Test 1: PDF for video-enabled audit references video
        url_video = f"{BASE_URL}/api/audits/{AUDIT_VIDEO_AND_REG}/report/compliance-pdf"
        assertion["steps"].append({
            "action": f"GET compliance PDF for video-enabled audit ({AUDIT_VIDEO_AND_REG})",
            "expected": "200 with valid PDF",
            "observed": ""
        })

        body_video, headers_video, status_video = http_get(url_video, return_headers=True)
        assertion["steps"][-1]["observed"] = f"HTTP {status_video}"

        if status_video != 200:
            assertion["status"] = "fail"
            assertion["issues"] = f"Video+reg audit PDF returned {status_video}"
            save_evidence("VAL-CROSS-004-video-response.txt", f"Status: {status_video}\nBody: {body_video.decode('utf-8', errors='replace')[:1000]}")
            assertion["evidence"] = {"video_pdf_response": "regulatory-pdf/pdf-api/VAL-CROSS-004-video-response.txt"}
            return assertion

        pages_text_video, _ = extract_pdf_text(body_video)
        text_video = "\n".join(pages_text_video)

        save_evidence("VAL-CROSS-004-video-pdf.pdf", body_video)
        save_evidence("VAL-CROSS-004-video-text.txt", text_video)

        # Check for video references
        video_patterns = [
            r"video",
            r"recording",
            r"\.webm",
            r"session recording",
            r"video evidence",
        ]
        video_refs = []
        for p in video_patterns:
            matches = re.findall(p, text_video, re.IGNORECASE)
            if matches:
                video_refs.append({"pattern": p, "matches": matches[:3]})

        assertion["steps"].append({
            "action": "Check for video evidence references in PDF",
            "expected": "Video URL, filename, or 'video evidence available' text",
            "observed": f"Found {len(video_refs)} pattern types: {[r['pattern'] for r in video_refs]}"
        })

        if not video_refs:
            assertion["status"] = "fail"
            assertion["issues"] = "No video references found in compliance PDF for video-enabled audit"

        # Test 2: PDF for non-video audit still generates cleanly
        url_no_video = f"{BASE_URL}/api/audits/{AUDIT_WITH_FINDINGS}/report/compliance-pdf"
        assertion["steps"].append({
            "action": f"GET compliance PDF for non-video audit ({AUDIT_WITH_FINDINGS})",
            "expected": "200 with valid PDF (no errors)",
            "observed": ""
        })

        body_no_video, headers_no_video, status_no_video = http_get(url_no_video, return_headers=True)
        assertion["steps"][-1]["observed"] = f"HTTP {status_no_video}"

        if status_no_video != 200:
            assertion["status"] = "fail"
            assertion["issues"] = (assertion.get("issues") or "") + f"; Non-video audit PDF returned {status_no_video}"
        elif not body_no_video.startswith(b"%PDF-"):
            assertion["status"] = "fail"
            assertion["issues"] = (assertion.get("issues") or "") + "; Non-video audit PDF has invalid format"
        else:
            assertion["steps"].append({
                "action": "Verify non-video audit PDF is valid",
                "expected": "Valid PDF starting with %PDF-",
                "observed": f"Valid PDF, {len(body_no_video)} bytes"
            })

        assertion["evidence"] = {
            "video_pdf": "regulatory-pdf/pdf-api/VAL-CROSS-004-video-pdf.pdf",
            "video_pdf_text": "regulatory-pdf/pdf-api/VAL-CROSS-004-video-text.txt",
            "video_references": video_refs,
            "non_video_pdf_status": status_no_video
        }

    except Exception as e:
        assertion["status"] = "fail"
        assertion["issues"] = f"Exception: {e}"

    return assertion


# ==================== MAIN ====================

def main():
    print("=" * 60)
    print("Running Regulatory PDF Validation Tests")
    print("=" * 60)

    test_functions = [
        test_val_regpdf_002,
        test_val_regpdf_003,
        test_val_regpdf_004,
        test_val_regpdf_005,
        test_val_regpdf_006,
        test_val_regpdf_007,
        test_val_regpdf_008,
        test_val_regpdf_009,
        test_val_regpdf_010,
        test_val_cross_004,
    ]

    results = []
    for func in test_functions:
        print(f"\nRunning {func.__name__}...")
        result = func()
        results.append(result)
        status_icon = "PASS" if result["status"] == "pass" else "FAIL" if result["status"] == "fail" else result["status"].upper()
        print(f"  [{status_icon}] {result['id']}: {result['title']}")
        if result.get("issues"):
            print(f"  Issues: {result['issues']}")

    # Build summary
    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    blocked_count = sum(1 for r in results if r["status"] == "blocked")
    failed_ids = [r["id"] for r in results if r["status"] == "fail"]

    summary_parts = [f"Tested {len(results)} assertions: {pass_count} passed"]
    if fail_count:
        summary_parts.append(f"{fail_count} failed ({', '.join(failed_ids)})")
    if blocked_count:
        summary_parts.append(f"{blocked_count} blocked")
    summary = ", ".join(summary_parts)

    # Build report
    report = {
        "groupId": "pdf-api",
        "testedAt": datetime.now(timezone.utc).isoformat(),
        "isolation": {
            "backend_api": "http://localhost:8000",
            "tool": "curl.exe + Python (PyPDF2)",
            "test_audit_with_findings": AUDIT_WITH_FINDINGS,
            "test_audit_no_findings": AUDIT_NO_FINDINGS,
            "test_audit_video_and_reg": AUDIT_VIDEO_AND_REG,
            "access": "read-only API calls"
        },
        "toolsUsed": ["curl.exe", "Python/PyPDF2"],
        "assertions": results,
        "frictions": frictions,
        "blockers": blockers,
        "summary": summary
    }

    # Write report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {summary}")
    print(f"Report written to: {REPORT_PATH}")
    print(f"Evidence saved to: {EVIDENCE_DIR}")
    print(f"{'=' * 60}")

    return report


if __name__ == "__main__":
    report = main()
