# Environment

Environment variables, external dependencies, and setup notes.

**What belongs here:** Required env vars, external API keys/services, dependency quirks, platform-specific notes.
**What does NOT belong here:** Service ports/commands (use `.factory/services.yaml`).

---

## Platform
- Windows 10 (win32 10.0.26200)
- Python 3.12.9 (venv at backend/.venv)
- Node.js 24.13.0
- No Docker available

## Key Environment Variables
- `AUDIT_MODE`: auto|mock|hybrid|live (default: auto, falls back to mock)
- `DATABASE_URL`: SQLite for dev (default), PostgreSQL for prod
- `NOVA_ACT_API_KEY`: Required for hybrid/live mode
- `AWS_*`: Required for live mode and S3 storage
- `S3_BUCKET_NAME` + `S3_ENDPOINT_URL`: Required for S3 storage provider

## Dependencies
- Backend: fastapi, sqlalchemy, alembic, nova-act, boto3, xhtml2pdf, playwright, jinja2, structlog
- Frontend: react 19, react-router-dom 6, vite 6, typescript 5.8, tailwindcss 4
- No additional packages needed for video replay (nova-act already supports record_video)

## Windows-Specific Notes
- Use `backend\.venv\Scripts\python.exe` (not Scripts/python)
- Use `backend\.venv\Scripts\activate` for venv activation
- Path separators: use backslashes in Windows commands, forward slashes in Python/Node
