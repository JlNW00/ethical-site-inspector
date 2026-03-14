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

## Known Constraints
- Mock mode only for development — no real Nova Act or AWS Bedrock
- Videos in mock mode will be placeholder .webm files
- SQLite database (no concurrent write safety — but workers don't run concurrently)
