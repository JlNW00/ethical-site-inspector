# AGENTS.md — EthicalSiteInspector

## Overview
EthicalSiteInspector is a full-stack application that audits websites for manipulative UX ("dark patterns"). It has a FastAPI Python backend and a React TypeScript frontend.

## Repository Structure
```
backend/     — FastAPI + SQLAlchemy + Playwright + Alembic
frontend/    — React + Vite + TypeScript
data/        — SQLite DB, screenshots, reports (gitignored content)
```

## Quick Start (Single Command)
```bash
# Backend
cd backend && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements-dev.txt && alembic upgrade head && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## Build Commands
| Component | Command | Description |
|-----------|---------|-------------|
| Backend install | `pip install -r requirements-dev.txt` | Install all dependencies |
| Backend run | `uvicorn app.main:app --reload` | Start dev server on :8000 |
| Backend lint | `ruff check app/` | Lint Python code |
| Backend format | `ruff format app/` | Format Python code |
| Backend typecheck | `mypy app/ --ignore-missing-imports` | Type check with mypy |
| Backend test | `pytest tests/ -v --tb=short --durations=10` | Run pytest suite |
| Backend coverage | `pytest tests/ --cov=app --cov-fail-under=50` | Run with coverage |
| Frontend install | `npm install` | Install Node dependencies |
| Frontend run | `npm run dev` | Start Vite dev server on :5173 |
| Frontend lint | `npm run lint` | ESLint check |
| Frontend format | `npm run format` | Prettier format |
| Frontend typecheck | `npx tsc -b` | TypeScript strict check |
| Frontend test | `npm test` | Run Vitest suite |
| Frontend build | `npm run build` | Production build |

## Architecture
- **Layered architecture**: Routes → Orchestrator → Providers (browser/classifier/storage)
- **Strategy pattern**: Mock, hybrid, and live providers selected by configuration
- **Three audit modes**: mock (simulated), hybrid (real browser + mock AI), live (real browser + Nova AI)

## Coding Conventions
- Python: Follow PEP 8, enforced by ruff. Use type hints everywhere (mypy strict).
- TypeScript: Strict mode enabled. Use camelCase for functions/variables, PascalCase for types/components.
- API routes return Pydantic models; never raw dicts.
- All database access goes through SQLAlchemy sessions from `get_db()`.
- Providers implement abstract base classes (ABC pattern).
- Test files: `test_*.py` for Python, `*.test.ts(x)` for TypeScript.

## Environment Variables
See `backend/.env.example` and `frontend/.env.example` for required env vars.

## Naming Conventions
- **Python**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **TypeScript**: camelCase for functions/variables, PascalCase for components/interfaces/types, UPPER_CASE for constants
- **Files**: snake_case for Python files, PascalCase for React components, camelCase for other TS files
- **Tests**: `test_<module>.py` for Python, `<module>.test.ts(x)` for TypeScript

## Log Scrubbing
Sensitive data (AWS keys, database URLs, user tokens) must never appear in log output. All logging should use structured loggers that redact sensitive fields. See backend logging configuration.

## Runbooks
Incident response procedures are documented at:
- [Backend Health Check](backend/.env.example) — Monitor `/api/health` and `/api/readiness`
- For production issues: check Render dashboard logs, verify DATABASE_URL connectivity, confirm AWS credentials if using live mode
- Rollback: redeploy previous Render revision via dashboard
