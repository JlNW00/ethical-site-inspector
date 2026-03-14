---
name: backend-dev
description: Backend development for EthicalSiteInspector FastAPI application — models, schemas, providers, services, routes, tests
---

# Backend Developer

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Use for features that involve:
- Database models and Alembic migrations
- Pydantic schemas (request/response)
- FastAPI API endpoints
- Service layer logic (orchestrator, providers, report generation)
- Backend test coverage
- Python code quality fixes (mypy, ruff)

## Work Procedure

### 1. Understand the Feature
- Read the feature description, preconditions, expectedBehavior, and verificationSteps from features.json
- Read `AGENTS.md` for coding conventions and boundaries
- Read relevant `.factory/library/` files for architectural context
- Identify which existing files need modification and which new files to create

### 2. Write Tests First (TDD Red Phase)
- Create or update test file in `backend/tests/test_<feature>.py`
- Write test cases covering ALL expectedBehavior items from the feature spec
- Include edge cases: empty input, invalid input, boundary values, error conditions
- For API tests: create a local `api_test_client` fixture including the relevant router
- For model tests: use `db_session` fixture from conftest.py
- Run tests to confirm they FAIL: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_<feature>.py -v`
- Record the failing test output

### 3. Implement (TDD Green Phase)
- Create/modify files in this order:
  1. **Models** (`app/models/`) — New tables, columns. Create Alembic migration.
  2. **Schemas** (`app/schemas/`) — Pydantic request/response models
  3. **Providers/Services** (`app/services/`, `app/providers/`) — Business logic
  4. **Routes** (`app/api/routes/`) — API endpoints, wire to router in `app/api/__init__.py`
  5. **Templates** (`app/templates/`) — Jinja2 templates if needed
- Follow existing patterns exactly (check similar files first)
- Alembic migrations: `cd backend && .venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"`
- Then apply: `cd backend && .venv\Scripts\python.exe -m alembic upgrade head`

### 4. Verify Tests Pass (TDD Green Confirmation)
- Run your new tests: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_<feature>.py -v`
- Run the FULL test suite: `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v --tb=short`
- ALL tests must pass (both new and existing)

### 5. Lint and Type Check
- Run ruff: `cd backend && .venv\Scripts\python.exe -m ruff check app/ --fix`
- Run ruff format: `cd backend && .venv\Scripts\python.exe -m ruff format app/`
- Run mypy: `cd backend && .venv\Scripts\python.exe -m mypy app/ --ignore-missing-imports`
- Fix any issues introduced by your changes

### 6. Manual Verification
- Start the backend server: `cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000` (fire and forget)
- Wait for startup, then test your endpoints with curl:
  - Hit the new/modified endpoint(s) with valid input
  - Hit with invalid input to verify error handling
  - Verify response schema matches Pydantic model
- Stop the server after testing
- Record each curl command, response status, and key observations

### 7. Update Shared Knowledge
- If you discover something other workers need to know, update `.factory/library/architecture.md` or `.factory/library/environment.md`

## Example Handoff

```json
{
  "salientSummary": "Implemented Benchmark model, schemas, and CRUD API endpoints (POST /api/benchmarks, GET /api/benchmarks, GET /api/benchmarks/{id}). Benchmark creation spawns individual audits per URL. Wrote 12 tests covering creation, validation, listing, and partial failure. All 265 tests pass, ruff clean, mypy clean.",
  "whatWasImplemented": "New Benchmark SQLAlchemy model with id, status, urls (JSON), audit_ids (JSON), created_at, updated_at. BenchmarkCreate and BenchmarkRead Pydantic schemas. Three API routes on /api/benchmarks router. Alembic migration 20260314_0001_add_benchmarks_table.py. Mock benchmark creation spawns audits sequentially.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "cd backend && .venv\\Scripts\\python.exe -m pytest tests/test_benchmarks_api.py -v",
        "exitCode": 0,
        "observation": "12 tests passed: create benchmark (201), validation errors (422 for <2 URLs, >5 URLs, invalid URLs), get by id (200/404), list (200 with ordering), partial failure handling"
      },
      {
        "command": "cd backend && .venv\\Scripts\\python.exe -m pytest tests/ -v --tb=short",
        "exitCode": 0,
        "observation": "265 passed, 1 warning. No regressions."
      },
      {
        "command": "cd backend && .venv\\Scripts\\python.exe -m ruff check app/",
        "exitCode": 0,
        "observation": "No lint errors"
      },
      {
        "command": "curl -X POST http://localhost:8000/api/benchmarks -H 'Content-Type: application/json' -d '{\"urls\":[\"https://example.com\",\"https://example.org\"],\"selected_scenarios\":[\"cookie_consent\"],\"selected_personas\":[\"privacy_sensitive\"]}'",
        "exitCode": 0,
        "observation": "201 Created. Response: {id: uuid, status: 'queued', urls: [...], audit_ids: [uuid1, uuid2], created_at: ...}"
      }
    ],
    "interactiveChecks": []
  },
  "tests": {
    "added": [
      {
        "file": "tests/test_benchmarks_api.py",
        "cases": [
          {"name": "test_create_benchmark_happy_path", "verifies": "POST /api/benchmarks with 2 valid URLs returns 201"},
          {"name": "test_create_benchmark_min_urls", "verifies": "POST with <2 URLs returns 422"},
          {"name": "test_create_benchmark_max_urls", "verifies": "POST with >5 URLs returns 422"},
          {"name": "test_get_benchmark_by_id", "verifies": "GET /api/benchmarks/{id} returns 200"},
          {"name": "test_get_benchmark_not_found", "verifies": "GET /api/benchmarks/{invalid} returns 404"},
          {"name": "test_list_benchmarks", "verifies": "GET /api/benchmarks returns sorted list"}
        ]
      }
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Feature depends on a frontend component or page that doesn't exist yet
- Alembic migration conflicts with another migration
- Existing test fixtures are insufficient and need structural changes to conftest.py
- A provider ABC needs new methods that would affect other providers
- You discover that the feature scope is significantly larger than described
