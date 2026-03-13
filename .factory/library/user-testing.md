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
- Run Page: http://127.0.0.1:5173/audits/{id}
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
