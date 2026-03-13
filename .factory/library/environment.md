# Environment

Environment variables, external dependencies, and setup notes.

**What belongs here:** Required env vars, external API keys/services, dependency quirks, platform-specific notes.
**What does NOT belong here:** Service ports/commands (use `.factory/services.yaml`).

---

## Platform
- Windows 10, 64-bit
- Python 3.12.9 in backend/.venv
- Node 24.13.0 / npm 11.6.2
- Git 2.53.0

## AWS Configuration
- Credentials stored in `backend/.env` (loaded via pydantic-settings + dotenv)
- Region: us-east-1
- Nova Model ID: us.amazon.nova-premier-v1:0 (for Bedrock classification)
- Nova Act: uses IAM auth via boto3 default session (credentials from env)

## Key Dependencies
- nova-act >= 3.1.263.0 (pip install nova-act)
- playwright 1.58.0 (chromium installed)
- boto3 1.42.66
- fastapi 0.135.1
- sqlalchemy 2.0.x
- React 18.3.x, Vite 6.2.x

## Database
- SQLite at data/ethicalsiteinspector.db
- Migrations via Alembic (single initial migration exists)

## Nova Act SDK Notes
- Requires Python >= 3.10 (we have 3.12)
- First run may take 1-2 min to install Playwright modules
- Uses Chromium by default (Google Chrome optional)
- Each NovaAct session is single-threaded; parallelize via ThreadPoolExecutor
- Headless mode: `NovaAct(starting_page=url, headless=True, tty=False)`
- For IAM auth: just ensure AWS credentials in environment, SDK picks them up automatically
- act() for actions, act_get() for data extraction with Pydantic schemas
- nova.page gives direct Playwright Page access for screenshots/DOM
