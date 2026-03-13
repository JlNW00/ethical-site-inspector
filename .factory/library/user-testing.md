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

## Flow Validator Guidance: Web Browser (ui-demo)

### Testing Approach
For ui-demo milestone assertions, the primary testing surface is the web browser at http://127.0.0.1:5173 backed by the API at http://127.0.0.1:8000. Use `agent-browser` skill for all browser automation.

### Services Running
- Backend API: http://127.0.0.1:8000 (health check passing)
- Frontend: http://127.0.0.1:5173 (Vite dev server)

### Available Test Data
The database has 22 audits with the following notable entries:
- **Audit with findings (booking.com)**: ID `adcde59c-d03d-41c5-be90-9fdf4d3e96f8` - trust_score=26.0, risk_level=critical, 3 findings, scenarios=checkout_flow, personas=privacy_sensitive/cost_sensitive/exit_intent (3 personas - good for diff view)
- **Completed audits with multiple personas**: ID `87a270b4-ab32-4068-92df-204ddca23e00` (example.com), ID `c10a9583-e82a-4be4-8473-d64ab47d0504` (example.com) - both with 2 scenarios, 2 personas
- **Completed live audit**: ID `16aa958c-f640-4bff-9577-baa4635ac362` (nonexistent domain, 0 findings)
- **Running audits**: 2 audits currently in "running" status (stuck from previous sessions)
- **No failed audits exist** - VAL-UI-011 must check error states with available data (running/completed)

### Key Pages and Routes
- `/` - SubmitPage (home): Form to submit new audit with URL, scenarios, personas
- `/history` - HistoryPage: Lists all audits with status badges, search, filter, compare
- `/audits/:id/run` - RunPage: Shows audit progress with polling, events timeline
- `/audits/:id/report` - ReportPage: Full report with findings, screenshots, PDF download
- `/audits/:id/diff` - PersonaDiffPage: Side-by-side persona comparison
- `/compare?a=:id1&b=:id2` - ComparePage: Compare two audits

### Recommended Audit IDs for Testing
- For history/listings: Navigate to /history - should show 20+ audits
- For report with findings: Use `adcde59c-d03d-41c5-be90-9fdf4d3e96f8` (booking.com, has 3 findings)
- For persona diff: Use `adcde59c-d03d-41c5-be90-9fdf4d3e96f8` (has 3 personas)
- For compare: Select any 2 completed audits from history
- For submit/run: Submit a new mock audit from the home page

### Isolation Rules
- Do NOT modify any application code
- Do NOT stop services
- Each browser session should use a unique session ID based on group name
- Browser tests are read-only against the same server - no shared state conflicts
- Multiple validators can run concurrently without interference

### agent-browser Session Naming
Use session format: `7b3986a5a96e__<group>` where group is the validator group name (e.g., `7b3986a5a96e__histnav`, `7b3986a5a96e__report`, etc.)

### Common Gotchas
- On Windows, PowerShell `curl` is an alias for Invoke-WebRequest - use Python urllib instead for API calls
- The frontend uses a glass-morphism dark theme with CSS transitions
- Some pages use polling (RunPage) - wait for content to load
- PDF download uses the browser's download mechanism
