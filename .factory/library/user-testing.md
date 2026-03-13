# User Testing

Testing surface, validation approach, and resource classification.

---

## Validation Surface

### Web Browser (Primary)
- Frontend: http://127.0.0.1:5173 (Vite dev server)
- Backend API: http://127.0.0.1:8000 (FastAPI/uvicorn)
- Tool: agent-browser
- Pages to test: SubmitPage (/), RunPage (/audits/:id/run), ReportPage (/audits/:id/report), HistoryPage (new), PersonaDiffView (new)

### API Endpoints (Secondary)
- Tool: curl
- Key endpoints: POST /api/audits, GET /api/audits/{id}, GET /api/audits/{id}/findings, GET /api/audits/{id}/report, GET /api/health, GET /api/readiness

## Validation Concurrency

### Machine Specs
- 32 GB RAM, 16 logical cores
- Baseline usage: ~19.5 GB (~60%)
- Free headroom: ~13 GB
- 70% budget: ~9.1 GB

### agent-browser Surface
- Dev server: ~200 MB
- Each agent-browser instance: ~300 MB
- 5 instances: ~1.5 GB + 200 MB server = ~1.7 GB
- **Max concurrent validators: 5** (well within 9.1 GB budget)

## Test Data Requirements
- Need at least 2 completed audits in the database for history/compare testing
- Need at least 1 failed audit for error state testing
- Audits should have findings with different personas for diff view testing

## Known Limitations
- Nova Act live audits take 30-120 seconds per scenario — testing with real Nova Act is slow
- For UI validation, mock/seeded data in the database may be needed
- Cookie consent testing depends on the target site actually having a cookie banner
