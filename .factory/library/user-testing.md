# User Testing Knowledge — EthicalSiteInspector

## Service URLs
- Backend API: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:5173
- Health check: GET http://127.0.0.1:8000/api/health
- Readiness: GET http://127.0.0.1:8000/api/readiness

## Starting Services
- Backend: `cd C:\EthicalSiteInspector\backend && Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--port","8000","--host","127.0.0.1" -NoNewWindow -PassThru`
- Frontend: `cd C:\EthicalSiteInspector\frontend && Start-Process -FilePath "cmd" -ArgumentList "/c","npm run dev -- --port 5173" -NoNewWindow -PassThru`
- Stop services: `powershell -ExecutionPolicy Bypass -File C:\EthicalSiteInspector\.factory\scripts\stop-services.ps1`

## Seed Data
- Data is pre-seeded via backend seed service on startup
- Multiple completed audits exist (mock mode), e.g., audit ID `44315460-1610-4bee-9b32-7d544c5bbb12`
- GET http://127.0.0.1:8000/api/audits lists all audits

## PDF Export
- Endpoint: GET http://127.0.0.1:8000/api/audits/{id}/report/pdf
- Returns application/pdf content type
- CSS variables are resolved before PDF rendering (fix applied in fix-pdf-css-variables feature)
- xhtml2pdf is the PDF generation library

## Frontend Pages
- Home / Submit: http://127.0.0.1:5173/
- History: http://127.0.0.1:5173/history
- Run Page: http://127.0.0.1:5173/audits/{id}/run (NOTE: route is /audits/:id/run, NOT /audits/:id)
- Report Page: http://127.0.0.1:5173/audits/{id}/report
- Persona Diff: http://127.0.0.1:5173/audits/{id}/diff
- Compare: http://127.0.0.1:5173/compare?a={id1}&b={id2}

## Validation Concurrency
- Max concurrent validators: 5 (per mission.md)
- Each agent-browser instance uses ~300MB, server ~200MB

## Flow Validator Guidance: Web Browser

### Testing Tool
Use `agent-browser` skill for UI testing. Invoke via Skill tool at session start.

### Isolation
- All validators share the same backend/frontend instances
- Read-only operations (viewing pages, downloading PDFs) don't conflict
- Write operations (creating audits, rerunning) may conflict — use unique URLs
- For PDF testing: use existing completed audits, don't create new ones

### Key Patterns
- PDF download: On report page, click "Download PDF" button or directly access API endpoint
- The PDF button opens a new tab with the PDF URL
- Navigation: Use top nav links (Home, History) to navigate between pages
- All pages use glass-morphism dark theme styling

### Gotchas
- Frontend is a SPA (React) — page transitions don't trigger full page loads
- API responses may take a moment — wait for loading indicators to disappear
- PDF generation can take a few seconds for large reports

## Advanced Intelligence Data Context

### Audits with Findings
Most findings are from live booking.com audits. The best audit for testing UI display is:
- `6af01314-92fe-45f4-bc3d-07e07c535898` — 28 findings from booking.com (good for UI testing)
- `cd8af7ae-0511-48bd-b5ef-097914f691d3` — 20 findings from booking.com
- `88640c48-5ad8-45fa-b592-5f49608799bf` — 5 findings from example.com

### Data Fields Present on Findings
All findings have these advanced fields in the API response:
- `regulatory_categories` (list of strings) — present but may be `[]` for older findings seeded before the feature was wired in
- `confidence` (float 0.0-1.0) — always populated, varies by evidence quality
- `suppressed` (boolean) — present, defaults to false
- `evidence_payload.source_label` (string) — present in some findings
- `evidence_payload.evidence_type` (string) — present in some findings

### Regulatory Mapping in Code
The regulatory mapping IS correctly wired in the orchestrator code:
- `get_regulations_for_pattern_family()` maps pattern families to regulations
- Pattern families: asymmetric_choice → [FTC, DSA], hidden_costs → [FTC, GDPR, DSA], etc.
- The code at `audit_orchestrator.py:219` correctly calls this function for new findings
- Existing DB findings have empty arrays because they were seeded before this code was added

### Frontend Components for Advanced Features
- FindingCard.tsx shows regulatory badges, confidence percentage, source labels
- Suppressed findings get muted styling and "Likely false positive" badge
- ReportPage.tsx executive summary shows suppressed count

## Flow Validator Guidance: API Testing

### Testing Tool
Use `curl` or Python `urllib` directly for API assertions.

### Key API Endpoints
- GET /api/audits — list all audits
- GET /api/audits/{id} — audit details with events
- GET /api/audits/{id}/findings — findings with regulatory_categories, confidence, suppressed
- GET /api/audits/{id}/report/pdf — PDF download
- POST /api/audits — create new audit
- GET /api/readiness — readiness check with provider info

### Isolation
- API read operations are safe for concurrent access
- Creating audits (POST) may run background tasks but won't conflict with reads
