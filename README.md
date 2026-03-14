# EthicalSiteInspector

**AI-powered ethical auditing tool that uses Amazon Nova Act to behaviorally test websites for dark patterns.**

Built for the [Amazon Nova AI Hackathon](https://amazonnovaai.devpost.com/) — UI Automation track.

---

## What It Does

EthicalSiteInspector autonomously navigates real websites as different user personas, detects manipulative UX patterns (dark patterns), and generates evidence-backed trust reports with regulatory mappings.

**Key capabilities:**
- **Nova Act browser automation** — AI agent navigates cookie consent flows, checkout processes, subscription cancellations, account deletion, newsletter signups, and pricing pages
- **Multi-persona testing** — Tests the same site as privacy-sensitive, cost-sensitive, and exit-intent users to surface discriminatory UX
- **Structured evidence extraction** — Screenshots, DOM observations, and behavioral data captured at each step using `act_get()` with Pydantic schemas
- **Dark pattern taxonomy** — 6 categories (manipulative design, deceptive content, coercive flow, obstruction, sneaking, social proof manipulation) across 6 audit scenarios
- **Regulatory mapping** — Findings automatically mapped to FTC, GDPR, DSA, and CPRA guidelines
- **False positive suppression** — Rule-based suppression engine reduces noise from known-benign patterns
- **Trust scoring** — Quantitative trust score (0-100) computed from weighted findings
- **PDF & HTML reports** — Exportable audit reports with evidence and regulatory references
- **Persona diff view** — Side-by-side comparison of how different personas experience the same site
- **Audit history** — Browse, filter, compare, and rerun past audits
- **Nova Act video replay** — Browser session recordings (.webm) per scenario/persona, viewable on ReportPage
- **Comparative benchmark mode** — Multi-URL (2-5) side-by-side dark pattern comparison with trust score ranking
- **Regulatory compliance PDF** — Formal per-regulation reports (FTC, GDPR, DSA, CPRA) with article citations and compliance matrix
- **AWS CloudFormation deployment** — Production infrastructure template (EC2, RDS, S3, ALB) with deployment scripts

## How Nova Is Used

Nova Act SDK (`nova-act`) is the core browser automation engine. The `NovaActAuditProvider` uses:

- **`NovaAct(starting_page=url, headless=True)`** to create browser sessions
- **`nova.act("...")`** for navigation actions (clicking buttons, filling forms, attempting cancellations)
- **`nova.act_get("...", schema=PydanticModel)`** for structured data extraction (prices, button labels, consent states, hidden fees)
- **`nova.page.screenshot()`** for evidence capture at key journey steps
- **`ThreadPoolExecutor`** for parallel persona testing within scenarios

Each of the 6 audit scenarios has dedicated Nova Act prompt chains designed to probe for specific dark patterns (e.g., asymmetric cookie consent buttons, hidden checkout fees, obstructive cancellation flows).

Nova on Bedrock (`LiveNovaClassifierProvider`) enriches findings with AI-powered reasoning, providing confidence scores and detailed explanations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│   Submit → Run (live events) → Report → History/Diff     │
│   BenchmarkPage (multi-URL comparison)                   │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                  FastAPI Backend                          │
│  Routes → AuditOrchestrator → Providers                  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Browser      │  │ Classifier   │  │ Storage       │  │
│  │ Provider     │  │ Provider     │  │ Provider      │  │
│  │ (Nova Act)   │  │ (Bedrock)    │  │ (Local/S3)    │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Rule Engine  │  │ Taxonomy     │  │ Suppression   │  │
│  │ (Heuristics) │  │ (Categories) │  │ Engine        │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              infrastructure/                              │
│  CloudFormation (EC2, RDS, S3, ALB) + deploy scripts     │
└─────────────────────────────────────────────────────────┘
```

**Strategy pattern** — All providers implement abstract base classes. Swap between mock, hybrid, and live modes via configuration:

| Mode | Browser | Classifier | When |
|------|---------|------------|------|
| Mock | Simulated data | Mock AI | No credentials needed |
| Hybrid | Nova Act / Playwright | Mock AI | `NOVA_ACT_API_KEY` set, no Bedrock creds |
| Live | Nova Act | Nova on Bedrock | Full AWS credentials |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Browser automation | Amazon Nova Act SDK (`nova-act`) |
| AI classification | Amazon Nova on Amazon Bedrock |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic |
| Frontend | React 18, Vite, TypeScript (strict mode) |
| Database | SQLite (dev), Postgres-ready via `DATABASE_URL` |
| PDF export | xhtml2pdf |
| Storage | Local filesystem (dev), S3-compatible (prod) |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Backend runs on http://127.0.0.1:8000.

### 2. Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend runs on http://127.0.0.1:5173.

### 3. Enable Live Mode (Optional)

For real browser automation with Nova Act:

```bash
# In backend/.env
NOVA_ACT_API_KEY=your-key-from-nova.amazon.com/act
```

For full live mode with AI classification:

```bash
# In backend/.env
USE_REAL_BROWSER=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
NOVA_MODEL_ID=us.amazon.nova-pro-v1:0
```

## Demo Flow

1. **Submit page** — Enter a URL, see mode/readiness badges, launch an audit; toggle "Benchmark Mode" for multi-URL comparison
2. **Run page** — Watch live activity events and evidence capture in real time
3. **Report page** — Trust score, scenario breakdown, finding cards with evidence, screenshot timeline, PDF download, "Session Recordings" video player section, and "Download Compliance Report" button
4. **Persona diff** — Side-by-side comparison of how different personas experienced the site
5. **History** — Browse past audits, filter by status, compare results, rerun audits
6. **Benchmark page** — Side-by-side trust score comparison across multiple URLs

Mock mode works immediately with no credentials — it seeds a demo audit on startup.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/readiness` | Readiness with effective mode info |
| `GET` | `/api/audits` | List all audits |
| `POST` | `/api/audits` | Create and start a new audit |
| `GET` | `/api/audits/{id}` | Get audit details |
| `GET` | `/api/audits/{id}/findings` | Get audit findings |
| `GET` | `/api/audits/{id}/report` | Get HTML report |
| `GET` | `/api/audits/{id}/report/pdf` | Download PDF report |
| `GET` | `/api/audits/{id}/report/compliance-pdf` | Download regulatory compliance PDF |
| `POST` | `/api/benchmarks` | Create benchmark (multi-URL audit) |
| `GET` | `/api/benchmarks` | List all benchmarks |
| `GET` | `/api/benchmarks/{id}` | Get benchmark details |

## Testing

```bash
# Backend (416 tests)
cd backend && .venv/bin/python -m pytest tests/ -v

# Frontend (220 tests)
cd frontend && npm test

# Full lint + type check
cd backend && ruff check app/ && mypy app/ --ignore-missing-imports
cd frontend && npm run lint && npx tsc -b
```

## Project Structure

```
backend/
  app/
    api/routes/          # FastAPI endpoints
    core/taxonomy.py     # Single source of truth for categories/scenarios/personas
    detectors/           # Rule engine + suppression engine
    extractors/          # Regulatory mapping, evidence extraction
    models/              # SQLAlchemy models (audits, findings, events)
    providers/           # Browser (Nova Act), classifier (Bedrock), storage
    schemas/             # Pydantic request/response models
    services/            # Audit orchestrator, report service, provider registry
    templates/           # HTML report templates
  alembic/               # Database migrations
  tests/                 # 416 backend tests
frontend/
  src/
    pages/               # SubmitPage, RunPage, ReportPage, HistoryPage, PersonaDiffPage, ComparePage, BenchmarkPage
    components/          # FindingCard, ModeBadge, ProgressMeter, Layout
    api/                 # API client and types
    constants/           # Frontend taxonomy (synced with backend)
    styles/              # Dark glassmorphism CSS theme
infrastructure/
  cloudformation.yaml    # AWS CloudFormation template (EC2, RDS, S3, ALB)
  deploy.sh              # Deployment script
  nginx/                 # Nginx configuration
  systemd/               # Systemd service files
  env.production.template # Production environment template
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `AUDIT_MODE` | `auto`, `mock`, `hybrid`, or `live` | `auto` |
| `USE_REAL_BROWSER` | Enable real browser execution | `false` |
| `DATABASE_URL` | SQLite or Postgres connection string | SQLite local |
| `NOVA_ACT_API_KEY` | Nova Act API key from nova.amazon.com/act | — |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `NOVA_MODEL_ID` | Bedrock model ID | `us.amazon.nova-pro-v1:0` |
| `AWS_ACCESS_KEY_ID` | AWS credentials for Bedrock | — |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for Bedrock | — |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend URL | `http://127.0.0.1:8000` |

## Deployment

`render.yaml` is included for Render deployment:
- Python web service for FastAPI
- Static site for the React frontend
- Managed Postgres

Set `DATABASE_URL`, AWS credentials, and `NOVA_MODEL_ID` as environment variables in your deployment platform.

## License

Hackathon project — not yet licensed for production use.
