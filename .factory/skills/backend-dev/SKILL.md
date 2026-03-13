---
name: backend-dev
description: Backend development for EthicalSiteInspector FastAPI application — Nova Act integration, API endpoints, tests
---

# Backend Developer

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features involving:
- Python/FastAPI backend code (providers, routes, services, models, schemas)
- Nova Act SDK integration
- Database models and migrations
- Backend test suites
- Taxonomy and classification logic

## Work Procedure

### 1. Understand the Feature
- Read the feature description, preconditions, expectedBehavior, and verificationSteps carefully
- Read `mission.md` and `AGENTS.md` for context and constraints
- Read `.factory/library/architecture.md` and `.factory/library/environment.md` for patterns
- Read `.factory/research/nova-act.md` for Nova Act SDK usage patterns
- Examine existing code in the relevant modules before writing new code

### 2. Write Tests First (TDD)
- Create or update test file(s) in `backend/tests/`
- Write failing tests that cover the expectedBehavior
- Use simple stubs/mocks for external dependencies (Nova Act, Bedrock) — do NOT use the existing MockBrowserAuditProvider
- Run tests to confirm they fail: `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v --tb=short -x`

### 3. Implement
- Write the implementation code
- Import dark pattern categories, scenarios, severity from `backend/app/core/taxonomy.py` — NEVER hardcode
- Follow existing patterns: Pydantic models for API responses, ABC for providers, get_db() for DB access
- Type hints on every function signature
- Keep imports clean and organized

### 4. Verify
- Run tests: `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v --tb=short -x`
- Run linter: `cd backend && .venv\Scripts\python.exe -m ruff check app/`
- Run formatter: `cd backend && .venv\Scripts\python.exe -m ruff format app/`
- Run typecheck: `cd backend && .venv\Scripts\python.exe -m mypy app/ --ignore-missing-imports`
- Fix ALL lint/type errors before committing
- If the feature adds/changes API endpoints, verify with curl

### 5. Manual Verification
- For API changes: start the server and test with curl
  ```
  cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
  curl http://127.0.0.1:8000/api/health
  curl http://127.0.0.1:8000/api/readiness
  ```
- For Nova Act provider: verify the provider is registered and selected in live mode
- Kill any started servers before completing

### 6. Commit
- Stage all changed files
- Write a clear commit message describing what was built
- Ensure no secrets or credentials in the diff

## Example Handoff

```json
{
  "salientSummary": "Implemented NovaActAuditProvider with IAM auth and 6 scenario prompt chains. Tests pass (12 new tests) using simple stubs. Verified provider registration via /api/readiness showing NovaActAuditProvider in live mode.",
  "whatWasImplemented": "Created backend/app/providers/nova_act_browser.py implementing BrowserAuditProvider ABC. Added 6 scenario methods (cookie_consent, checkout_flow, subscription_cancellation, account_deletion, newsletter_signup, pricing_comparison) using Nova Act act()/act_get() with Pydantic schemas. Updated provider_registry.py to select NovaActAuditProvider for live mode. Created backend/app/core/taxonomy.py as single source of truth for categories/scenarios/severity.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {"command": "cd backend && .venv\\Scripts\\python.exe -m pytest tests/ -v --tb=short -x", "exitCode": 0, "observation": "42 passed, 0 failed"},
      {"command": "cd backend && .venv\\Scripts\\python.exe -m ruff check app/", "exitCode": 0, "observation": "No issues found"},
      {"command": "cd backend && .venv\\Scripts\\python.exe -m mypy app/ --ignore-missing-imports", "exitCode": 0, "observation": "Success: no issues found"},
      {"command": "curl http://127.0.0.1:8000/api/readiness", "exitCode": 0, "observation": "browser_provider: NovaActAuditProvider, effective_mode: live"}
    ],
    "interactiveChecks": [
      {"action": "Started uvicorn, called /api/readiness", "observed": "Response shows NovaActAuditProvider as browser_provider in live mode"},
      {"action": "Called POST /api/audits with cookie_consent scenario", "observed": "Audit created with status queued, events show Nova Act execution"}
    ]
  },
  "tests": {
    "added": [
      {"file": "backend/tests/test_taxonomy.py", "cases": [{"name": "test_all_categories_defined", "verifies": "taxonomy has all 6 pattern categories"}, {"name": "test_all_scenarios_defined", "verifies": "taxonomy has all 6 audit scenarios"}]},
      {"file": "backend/tests/test_nova_act_provider.py", "cases": [{"name": "test_cookie_consent_scenario", "verifies": "cookie consent returns structured observations"}, {"name": "test_provider_selected_live_mode", "verifies": "registry selects NovaActAuditProvider for live mode"}]}
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Nova Act SDK installation fails or is incompatible with Python 3.12
- AWS credentials are not accessible from the backend environment
- Existing provider ABC interface needs changes that would break other providers
- Database schema changes require a new migration that conflicts with existing data
- Feature depends on frontend work that hasn't been done yet
