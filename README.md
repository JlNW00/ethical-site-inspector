# EthicalSiteInspector

EthicalSiteInspector is a full-stack hackathon project for the Amazon Nova AI Hackathon. It audits live website journeys for manipulative UX patterns, captures evidence, compares persona-specific outcomes, and generates a decision-ready HTML trust report.

## Why this project fits Nova

- Browser journey automation is a first-class product capability through the `BrowserAuditProvider` abstraction.
- Trust reasoning is a first-class product capability through the `ClassifierProvider` abstraction.
- Mock, hybrid, and live modes are wired through configuration so adding environment variables later turns on real integrations without code changes.
- The live classifier path is structured for Amazon Nova on Amazon Bedrock, including screenshot-aware evidence prompts.

## Stack

- Backend: FastAPI, SQLAlchemy 2.x, Alembic
- Frontend: React + Vite + TypeScript
- Browser automation: Playwright
- Database: SQLite locally, Postgres-ready via `DATABASE_URL`
- Storage: local filesystem locally, S3-compatible abstraction for production
- Reports: HTML

## Project structure

```text
backend/
  app/
    api/routes/
    core/
    detectors/
    extractors/
    models/
    providers/
    prompts/
    schemas/
    services/
    templates/
  alembic/
frontend/
  src/
data/
  reports/
  screenshots/
```

## Modes

### Mock mode

- No secrets required
- Full experience works end to end
- Seeds a completed demo audit on startup
- Uses realistic synthetic browser evidence and mock AI reasoning

### Hybrid mode

- Real Playwright browser execution
- Mock classifier if Nova credentials are not available

### Live mode

- Real Playwright browser execution
- Real Amazon Nova classification through Bedrock once AWS credentials are present

Mode selection is automatic by default:

- `AUDIT_MODE=auto` + no real-browser flag => `mock`
- `USE_REAL_BROWSER=true` + no Nova credentials => `hybrid`
- `USE_REAL_BROWSER=true` + AWS credentials => `live`

You can also force a mode explicitly with `AUDIT_MODE=mock|hybrid|live`.

## Local setup

### 1. Backend

```powershell
cd C:\EthicalSiteInspector\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Optional for hybrid/live browser runs:

```powershell
playwright install chromium
```

### 2. Frontend

```powershell
cd C:\EthicalSiteInspector\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Backend runs on `http://127.0.0.1:8000`.
Frontend runs on `http://127.0.0.1:5173`.

## Environment variables

### Backend

See [backend/.env.example](/C:/EthicalSiteInspector/backend/.env.example).

Important variables:

- `AUDIT_MODE`
- `USE_REAL_BROWSER`
- `DATABASE_URL`
- `AWS_REGION`
- `NOVA_MODEL_ID`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `S3_ENDPOINT_URL`

### Frontend

See [frontend/.env.example](/C:/EthicalSiteInspector/frontend/.env.example).

## API surface

- `POST /api/audits`
- `GET /api/audits/{id}`
- `GET /api/audits/{id}/findings`
- `GET /api/audits/{id}/report`
- `GET /api/health`
- `GET /api/readiness`

## Hackathon demo flow

1. Start with the submit page and show mode/readiness badges.
2. Launch an audit against a live site or open the seeded demo report instantly.
3. On the run page, highlight live activity events and evidence capture.
4. On the report page, show trust score, scenario breakdown, persona comparison, and HTML export.
5. If Bedrock credentials are available, flip on `USE_REAL_BROWSER=true` and AWS env vars to demonstrate live Nova reasoning.

## Deployment notes

`render.yaml` is included for an easy starting point:

- Python web service for FastAPI
- Static site for the React frontend
- Managed Postgres for production readiness

For production:

- Point `DATABASE_URL` at Postgres.
- Set `USE_REAL_BROWSER=true` if you want hybrid/live browser execution.
- Add AWS credentials and `NOVA_MODEL_ID` to enable live Nova classification.
- If you want object storage, set the S3 variables and the storage provider will switch without code changes.

## Notes

- No auth, billing, Docker, PDF generation, or CDK are included.
- The current browser audit heuristics are intentionally generic so the scaffold works across arbitrary sites. The provider seam is ready for a more specialized Nova Act-style browser agent later.
