# User Testing

Testing surface, tools, and resource cost classification for validation.

**What belongs here:** Testing surface details, tool setup, concurrency limits, runtime findings.

---

## Validation Surface
- **Primary surface:** Browser (React frontend at localhost:5173 proxying to backend at localhost:8000)
- **Tool:** agent-browser for all UI validation flows
- **Backend API:** Also testable via curl/httpx for API-level assertions

## Service Setup
1. Start backend: `cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npx vite --port 5173`
3. Health check: `curl -sf http://localhost:8000/api/health`
4. Frontend check: `curl -sf http://localhost:5173`

## Seed Data
- Mock mode auto-seeds a demo audit on startup
- For testing new features, create audits via `POST /api/audits` with default mock mode

## Validation Concurrency
- **Machine:** 31 GB RAM, 16 logical CPUs (8 cores)
- **Available headroom:** ~15 GB free RAM, using 70% = ~10.5 GB budget
- **Per validator:** ~300 MB (Chromium) + shared server overhead (~200 MB)
- **Max concurrent agent-browser validators:** 3
- **Rationale:** 3 x 300 MB + 200 MB server = 1.1 GB, well within 10.5 GB budget. Conservative limit of 3 to leave headroom for OS and background processes.

## Testing Approach
- agent-browser navigates the app, takes screenshots, checks console errors
- API-level assertions via curl for backend-only validation (PDF content, API responses)
- Video replay assertions need both API checks (video_url present) and browser checks (player renders)
- Deployment assertions are file/content checks (no browser needed)

## Flow Validator Guidance: Browser

**Surface:** React frontend at http://localhost:5173 (proxies API to backend at http://localhost:8000)

**Tool:** `agent-browser` skill (invoke via Skill tool at session start)

**Isolation rules:**
- All validators share the same backend/frontend instances — read-only access to existing audits is safe
- Do NOT create new audits during browser testing (use pre-created audit IDs)
- Do NOT modify database or files — read/navigate only
- Each validator uses its own browser session (pass `--session` flag)

**Pre-created test data:**
- Mock audit WITH video URLs (FRESH - round 3, fix applied): `08d0b4d2-967a-4ea6-afb5-dd888efc8a15` (4 video URLs, trust_score=100, mode=mock, completed, 185-byte known-good WebM files from mathiasbynens/small)
- Mock audit WITH video URLs (round 3 pre-fix): `c99e3e8f-856d-421e-8f0f-dcf8c41b2232` (4 video URLs, 212-byte invalid WebM files)
- Mock audit WITH video URLs (round 1-2, potentially stale): `e2ed0938-ca82-4e84-b76d-ec788e860c51` (4 video URLs, trust_score=100, mode=mock, completed)
- Old audit WITHOUT video URLs: `48fcd4cc-a0a4-454f-8444-4b3b302dd595` (video_urls=null, mode=mock, completed)

**Browser session naming:** Use `{worker-session-prefix}__{group-id}` pattern

**Key URLs:**
- ReportPage: `http://localhost:5173/audits/{audit_id}/report`
- PersonaDiffPage: `http://localhost:5173/audits/{audit_id}/diff` (NOT /persona-diff)
- RunPage: `http://localhost:5173/audits/{audit_id}/run`
- SubmitPage: `http://localhost:5173/`

**API endpoints (for curl checks from validators):**
- `GET http://localhost:8000/api/audits/{id}` — audit data with video_urls
- `HEAD http://localhost:8000/artifacts/videos/{audit_id}/{key}.webm` — video file check

## Flow Validator Guidance: API

**Surface:** Backend API at http://localhost:8000

**Tool:** curl.exe (use curl.exe on Windows, not curl alias)

**Isolation rules:**
- Do NOT create new audits — use pre-created audit IDs
- Read-only API calls only

**Pre-created test data:**
- Mock audit WITH video URLs: `e2ed0938-ca82-4e84-b76d-ec788e860c51`
- Old audit WITHOUT video URLs: `48fcd4cc-a0a4-454f-8444-4b3b302dd595`

## Benchmark Mode Test Data

**Completed benchmark:** `9b9d3b22-9571-4591-b6dd-4f4f199e17f3`
- Status: completed
- URLs: `https://example.com/`, `https://example.org/`
- Audit IDs: `94843e6d-5bfc-4ba5-a58b-3988450889ee` (example.com), `05251856-283b-462c-a8b1-795db5adf293` (example.org)
- Trust scores: both 100.0
- Selected scenarios: cookie_consent, subscription_cancellation
- Selected personas: privacy_sensitive, cost_sensitive
- Video URLs on audits: empty dict {} (benchmark audits created in mock mode)

**Key benchmark URLs:**
- BenchmarkPage: `http://localhost:5173/benchmarks/9b9d3b22-9571-4591-b6dd-4f4f199e17f3`
- Benchmark API: `http://localhost:8000/api/benchmarks/9b9d3b22-9571-4591-b6dd-4f4f199e17f3`
- Benchmarks list: `http://localhost:8000/api/benchmarks`
- Individual audit: `http://localhost:8000/api/audits/94843e6d-5bfc-4ba5-a58b-3988450889ee`

## Regulatory PDF Test Data

**IMPORTANT:** Mock audits in this app produce 0 findings because the mock browser provider doesn't set `scenario_state_found` in observation metadata (the rule engine gate). Test data with findings was manually seeded into the database.

**Audit WITH regulatory findings:** `regpdf-test-with-findings`
- target_url: https://darkpattern-example.com
- trust_score: 42.0, risk_level: high
- 5 findings with regulatory categories:
  - sneaking (GDPR, DSA, CPRA) — cookie_consent
  - asymmetric_choice (GDPR, DSA) — cookie_consent
  - hidden_costs (FTC, DSA) — checkout_flow
  - obstruction (FTC, CPRA) — subscription_cancellation
  - sneaking (FTC, GDPR, CPRA) — checkout_flow
- All 4 regulations represented: FTC, GDPR, DSA, CPRA
- video_urls: null

**Audit WITHOUT regulatory findings:** `regpdf-test-no-findings`
- target_url: https://clean-example.com
- trust_score: 95.0, risk_level: low
- 1 finding with empty regulatory_categories

**Audit WITH video + regulatory findings:** `regpdf-test-video-and-reg`
- target_url: https://video-regulatory-example.com
- trust_score: 55.0, risk_level: medium
- 2 findings with regulatory categories (GDPR, DSA, FTC, CPRA)
- video_urls present: cookie_consent_privacy_sensitive, checkout_flow_cost_sensitive

**Key endpoints:**
- Compliance PDF: `GET http://localhost:8000/api/audits/{id}/report/compliance-pdf`
- Findings: `GET http://localhost:8000/api/audits/{id}/findings`
- ReportPage: `http://localhost:5173/audits/{id}/report`

**Benchmark audit for VAL-CROSS-007:** Use `94843e6d-5bfc-4ba5-a58b-3988450889ee` from benchmark `9b9d3b22-9571-4591-b6dd-4f4f199e17f3` — note this benchmark audit has 0 findings (no regulatory categories), so the compliance PDF button should NOT be visible on its ReportPage. For testing CROSS-007 (per-URL regulatory PDF from benchmark), use the manually seeded `regpdf-test-with-findings` audit which HAS regulatory findings but is NOT part of a benchmark. Alternatively, test that the button is correctly ABSENT when there are no regulatory findings.

## Flow Validator Guidance: Deployment File Checks

**Surface:** Local filesystem — infrastructure files in `C:\EthicalSiteInspector\infrastructure\`

**Tool:** File reading (Read tool), shell commands (grep/search), curl.exe for backend API

**Isolation rules:**
- All validators are read-only file checks — no shared state concerns
- Mypy check requires backend venv but doesn't modify anything
- No servers need to be started for file content checks

**Infrastructure files:**
- CloudFormation template: `infrastructure/cloudformation.yaml`
- Deployment script: `infrastructure/deploy.sh`
- Nginx config: `infrastructure/nginx/ethicalsiteinspector.conf`
- Systemd service: `infrastructure/systemd/ethicalsiteinspector.service`
- Production env template: `infrastructure/env.production.template`

**Mypy check:**
- Run from: `cd C:\EthicalSiteInspector\backend && .venv\Scripts\python.exe -m mypy app/ --ignore-missing-imports`
- Expected: exit code 0, zero errors

## Known Constraints
- Mock mode only for development — no real Nova Act or AWS Bedrock
- Videos in mock mode will be placeholder .webm files
- SQLite database (no concurrent write safety — but workers don't run concurrently)
