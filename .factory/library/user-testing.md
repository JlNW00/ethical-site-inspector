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

## Flow Validator Guidance: API/Code Inspection

### Testing Approach
For nova-act-core milestone assertions, the primary testing surface is:
1. **Backend API** at http://127.0.0.1:8000 - verify endpoints return expected data structures
2. **Code inspection** - verify code structure, imports, and patterns via file reading
3. **Backend test suite** - verify all tests pass via pytest

### Services Running
- Backend API: http://127.0.0.1:8000 (already started, health check passing)
- Frontend: http://127.0.0.1:5173 (already started)

### Seeded Demo Audit
- ID: 87a270b4-ab32-4068-92df-204ddca23e00 (mock mode, completed)
- Use GET /api/audits/{id} and GET /api/audits/{id}/findings to inspect seeded data

## Flow Validator Guidance: Live Stability

### Testing Approach
For live-stability milestone assertions, the primary testing surfaces are:
1. **Backend API** at http://127.0.0.1:8000 - verify failure handling via API calls
2. **Code inspection** - verify timeout configuration, exception handling patterns
3. **Backend test suite** - verify all tests pass via pytest (VAL-STAB-004)

### Assertions to Verify
- VAL-STAB-001: Failed audits reach terminal state (status="failed" with error details)
- VAL-STAB-002: Error events emitted on failure (terminal event with phase="error")
- VAL-STAB-003: Timeout handling for long scenarios (configurable timeouts, graceful termination)
- VAL-STAB-004: Backend test suite passes (all tests green)

### Key Backend Files for Stability
- audit_orchestrator.py: `C:\EthicalSiteInspector\backend\app\services\audit_orchestrator.py` - main run_audit() method with exception handling
- audits.py: `C:\EthicalSiteInspector\backend\app\api\routes\audits.py` - API endpoints
- nova_act_browser.py: `C:\EthicalSiteInspector\backend\app\providers\nova_act_browser.py` - Nova Act provider with timeout configuration

### Testing Strategy for Failure States
- Create an audit via POST /api/audits with an unreachable/invalid URL to trigger failures
- Use mode=mock to avoid external Nova Act dependency for testing
- Check GET /api/audits/{id} for status="failed" and error details
- Check events array for phase="error" entries
- Inspect code for timeout configuration and graceful handling

### Backend Test Command
```
cd C:\EthicalSiteInspector\backend && .venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

### Key Backend Files
- taxonomy.py: `C:\EthicalSiteInspector\backend\app\core\taxonomy.py`
- nova_act_browser.py: `C:\EthicalSiteInspector\backend\app\providers\nova_act_browser.py`
- provider_registry.py: `C:\EthicalSiteInspector\backend\app\services\provider_registry.py`
- health.py: `C:\EthicalSiteInspector\backend\app\api\routes\health.py`

### Isolation Rules
- Do NOT modify any application code
- Do NOT start/stop services (they are already running)
- Use Python urllib or similar for API calls (curl on Windows uses PowerShell Invoke-WebRequest which has different syntax)
- Write reports to assigned output directories only

### API Call Pattern (Windows-compatible)
```python
C:\EthicalSiteInspector\backend\.venv\Scripts\python.exe -c "import urllib.request, json; r = urllib.request.urlopen('http://127.0.0.1:8000/api/health'); print(json.loads(r.read().decode()))"
```

### Backend Test Pattern
```
cd C:\EthicalSiteInspector\backend && .venv\Scripts\python.exe -m pytest tests/ -v --tb=short -x
```
