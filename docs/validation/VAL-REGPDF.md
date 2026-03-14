# Validation Contract: Regulatory Compliance PDF (VAL-REGPDF)

Feature area: Regulatory Compliance PDF report generation and download.

Scope: New dedicated regulatory compliance PDF document with per-regulation sections,
compliance matrix, executive summary, evidence references, dedicated API endpoint,
and frontend download button — distinct from the existing HTML-report PDF.

---

### VAL-REGPDF-001: Download Compliance Report button is visible on ReportPage

**Behavioral description:**
When ReportPage renders a completed audit that has at least one finding with a non-empty
`regulatory_categories` array, a button labeled **"Download Compliance Report"** is visible
in the action-row alongside the existing "Download PDF" and "Open HTML report" buttons.
The button must be an `<a>` element (or behave as a link) whose `href` points to the new
compliance PDF endpoint (`/api/audits/{id}/report/compliance-pdf`). It must open in a new
tab (`target="_blank"`).

**Pass condition:** Button is present in the DOM, visible, has the correct label text, and
its href matches `/api/audits/{auditId}/report/compliance-pdf`.

**Fail condition:** Button is missing, mislabeled, or points to the existing PDF endpoint.

**Evidence:** DOM snapshot or rendered screenshot of the ReportPage action-row; inspect the
`href` attribute value.

---

### VAL-REGPDF-002: Download Compliance Report button is hidden when no regulatory findings exist

**Behavioral description:**
When ReportPage renders a completed audit where every finding has an empty
`regulatory_categories` array (or the audit has zero findings), the
"Download Compliance Report" button must **not** be rendered. The existing
"Download PDF" button must still appear (it is regulation-agnostic).

**Pass condition:** Button is absent from the DOM.

**Fail condition:** Button appears despite no regulatory data being present.

**Evidence:** DOM snapshot or `queryByText("Download Compliance Report")` returns `null`
in a Vitest/RTL test with mock findings having empty `regulatory_categories`.

---

### VAL-REGPDF-003: API endpoint returns a valid PDF with correct headers

**Behavioral description:**
`GET /api/audits/{id}/report/compliance-pdf` returns an HTTP 200 response with:
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="compliance-report-{id}.pdf"` (or similar
  descriptive filename distinct from the existing `ethical-site-inspector-{id}.pdf`)
- Body begins with the `%PDF-` magic bytes, confirming it is a valid PDF document.

**Pass condition:** All three header/body checks pass.

**Fail condition:** Wrong content-type, missing disposition header, or body is not a valid PDF.

**Evidence:** Raw HTTP response headers and first 5 bytes of the body (`%PDF-`); optionally
parse with a PDF library (e.g., `PyPDF2`) to confirm page count > 0.

---

### VAL-REGPDF-004: Compliance PDF contains per-regulation sections for all implicated regulations

**Behavioral description:**
Given an audit whose findings collectively implicate regulations [FTC, GDPR, DSA, CPRA]
(via the `regulatory_categories` field and `REGULATORY_MAPPING` in taxonomy.py), the
generated compliance PDF must contain **four clearly titled sections**, one per regulation.
Each section heading must include the regulation abbreviation (e.g., "FTC", "GDPR") and
its full name (e.g., "Federal Trade Commission", "General Data Protection Regulation").

**Pass condition:** Extracted PDF text contains all four regulation section headings.

**Fail condition:** Any implicated regulation's section is missing from the PDF text.

**Evidence:** PDF text extraction (e.g., `pdfplumber` or `PyPDF2`) searching for each
regulation heading string.

---

### VAL-REGPDF-005: Each regulation section lists applicable findings with specific article/guideline citations

**Behavioral description:**
Within each regulation section, every finding whose `regulatory_categories` includes that
regulation is listed with:
1. Finding title and severity
2. At least one specific article, section, or guideline citation for that regulation
   (e.g., "FTC Act § 5", "GDPR Article 25 — Data Protection by Design", "DSA Article 25",
   "CPRA § 1798.140")
3. The finding's explanation or evidence excerpt

Findings that do not implicate a given regulation must **not** appear in that regulation's
section.

**Pass condition:** Every finding appears under the correct regulation(s), each with at
least one regulation-specific citation string. No finding appears under a regulation it
does not implicate.

**Fail condition:** Missing citations, findings listed under wrong regulations, or findings
omitted from applicable regulation sections.

**Evidence:** PDF text extraction; cross-reference each finding's `regulatory_categories`
against the sections it appears in; grep for citation patterns (article numbers, section
symbols).

---

### VAL-REGPDF-006: Compliance PDF includes a compliance matrix (regulations × scenarios)

**Behavioral description:**
The PDF contains a tabular compliance matrix with:
- Columns: one per regulation (FTC, GDPR, DSA, CPRA)
- Rows: one per audited scenario (e.g., cookie_consent, checkout_flow)
- Cell values indicating finding count, risk level, or pass/fail status for that
  regulation–scenario intersection

The matrix must cover all selected scenarios and all four regulations. Empty cells
(no findings for that intersection) must be explicitly marked (e.g., "✓", "0", "N/A",
or "Compliant").

**Pass condition:** Matrix is present with correct dimensions; cell values are consistent
with the underlying findings data.

**Fail condition:** Matrix is missing, has wrong dimensions, or cell values contradict the
actual findings.

**Evidence:** PDF text or table extraction; manually verify 2–3 cells against the audit's
findings data.

---

### VAL-REGPDF-007: Compliance PDF includes an executive summary with overall compliance posture

**Behavioral description:**
The first or second page of the PDF contains an executive summary section that includes:
1. Target URL audited
2. Audit date / timestamp
3. Total number of regulatory findings (excluding suppressed)
4. Which regulations are implicated
5. An overall compliance posture statement (e.g., "Non-compliant with FTC and GDPR",
   or "Potential exposure under 3 of 4 regulatory frameworks")
6. Trust score (if available)

**Pass condition:** All six data points are present and accurate relative to the audit data.

**Fail condition:** Executive summary is missing or any of the six data points is absent
or incorrect.

**Evidence:** PDF first-page text extraction; compare values against API response from
`GET /api/audits/{id}` and `GET /api/audits/{id}/findings`.

---

### VAL-REGPDF-008: Compliance PDF includes evidence references with screenshot links

**Behavioral description:**
Each finding listed in the regulation sections includes a reference to its supporting
evidence. Where a finding's `evidence_payload.screenshot_urls` is non-empty, the PDF must
include either:
- Embedded screenshot thumbnails, **or**
- Clickable hyperlinks to the screenshot URLs, **or**
- A labeled reference (e.g., "Evidence: screenshot_001") with a corresponding appendix

At minimum, the screenshot URL string or a reference identifier must appear in the PDF text
near the finding.

**Pass condition:** For findings with screenshots, evidence references are present in the
PDF. For findings without screenshots, no broken references appear.

**Fail condition:** Screenshot references are missing for findings that have them, or broken
links/references appear.

**Evidence:** PDF text extraction near each finding; verify screenshot URL strings or
reference identifiers are present.

---

### VAL-REGPDF-009: Compliance PDF is distinct from the existing HTML-report PDF

**Behavioral description:**
Downloading the existing PDF (`GET /api/audits/{id}/report/pdf`) and the new compliance PDF
(`GET /api/audits/{id}/report/compliance-pdf`) for the same audit produces two **different**
documents. Specifically:
1. File sizes differ (compliance PDF has regulation-specific structure)
2. The compliance PDF contains regulation section headings and a compliance matrix that
   the existing PDF does not
3. The existing PDF contains the full HTML report layout (trust score hero, persona
   comparison, scenario breakdown, etc.) which the compliance PDF may summarize differently
4. Filenames in `Content-Disposition` headers differ

**Pass condition:** Both PDFs are downloadable; byte content differs; compliance PDF contains
regulatory headings absent from the existing PDF.

**Fail condition:** Both endpoints return identical content, or the compliance endpoint
simply proxies the existing PDF.

**Evidence:** Download both files; compare file sizes, `Content-Disposition` filenames, and
grep for "Compliance Matrix" or regulation headings in each.

---

### VAL-REGPDF-010: Audit with findings across all 4 regulations produces a complete compliance PDF

**Behavioral description:**
Given an audit with findings spanning all six dark-pattern categories (which collectively
map to all four regulations per `REGULATORY_MAPPING` in taxonomy.py), the compliance PDF
must:
1. Contain all four regulation sections (FTC, GDPR, DSA, CPRA)
2. Have a compliance matrix with non-empty cells across multiple regulation columns
3. Executive summary references all four regulations
4. Total finding count in the PDF matches the count of non-suppressed findings with
   regulatory categories
5. PDF generates without errors (HTTP 200, valid PDF bytes)

**Pass condition:** All five checks pass.

**Fail condition:** Any regulation section is missing, matrix is incomplete, or PDF
generation fails.

**Evidence:** Use a seeded/mock audit with findings in all categories; download and parse
the compliance PDF; verify section count and matrix completeness.

---

### VAL-REGPDF-011: Audit with zero findings returns appropriate response from compliance PDF endpoint

**Behavioral description:**
When `GET /api/audits/{id}/report/compliance-pdf` is called for a completed audit with
zero findings (or all findings have empty `regulatory_categories`), the endpoint must
either:
- **Option A:** Return a valid PDF with a clear "No regulatory findings" message in the
  executive summary, empty compliance matrix, and no regulation sections, **or**
- **Option B:** Return HTTP 404 with a descriptive error message (e.g., "No regulatory
  findings to report")

Either behavior is acceptable as long as it is intentional, documented, and does not
produce a 500 error or a corrupt PDF.

**Pass condition:** Endpoint returns Option A or Option B cleanly without 500 error.

**Fail condition:** 500 Internal Server Error, corrupt/empty PDF, or misleading content
(e.g., showing regulation sections with zero findings without explanation).

**Evidence:** HTTP status code and response body/headers for an audit with no regulatory
findings.

---

### VAL-REGPDF-012: Compliance PDF has reasonable file size and professional formatting

**Behavioral description:**
The generated compliance PDF for a typical audit (6–12 findings across 2 scenarios and
2 personas) must:
1. Be between **10 KB and 5 MB** in size (not trivially empty, not excessively large)
2. Have at least **2 pages** (executive summary + regulation details)
3. Use consistent fonts, headings, and spacing (professional quality)
4. Not contain raw HTML tags, CSS artifacts, or rendering errors visible in the PDF
5. Page headers or footers include the application name ("EthicalSiteInspector") and/or
   audit identifier

**Pass condition:** File size is within range, page count ≥ 2, no rendering artifacts on
visual inspection.

**Fail condition:** PDF is under 10 KB (likely empty/broken), over 5 MB (bloated), single
page (missing content), or contains visible rendering errors.

**Evidence:** File size check, page count via PDF library, visual inspection of first 3
pages for layout quality.
