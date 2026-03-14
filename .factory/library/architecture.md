# Architecture

Architectural decisions, patterns, and conventions discovered during the mission.

**What belongs here:** Patterns, decisions, anti-patterns, architectural insights.

---

## Provider Pattern
All providers follow ABC → concrete implementation → registry selection:
- `BrowserAuditProvider` (ABC) → `MockBrowserAuditProvider`, `PlaywrightAuditProvider`, `NovaActAuditProvider`
- `ClassifierProvider` (ABC) → `MockClassifierProvider`, `LiveNovaClassifierProvider`
- `StorageProvider` (ABC) → `LocalStorageProvider`, `S3StorageProvider`

Selection happens in `provider_registry.py` based on Settings.

## Audit Flow
1. `POST /api/audits` → creates Audit record (queued)
2. Spawns daemon Thread → `run_audit()`
3. Browser provider runs scenarios per persona (ThreadPoolExecutor, max_workers=3)
4. Observations → Rule Engine → Finding drafts → Classifier → Findings
5. Report generation (Jinja2 HTML) → PDF available on-demand
6. Status: queued → running → completed/failed

## Database
- SQLAlchemy 2.0 with declarative models
- 3 tables: audits, findings, audit_events
- Alembic for migrations
- In-memory SQLite for tests (conftest.py)

## Frontend State Management
- No global store — useState + useEffect per page
- Polling pattern for live updates (RunPage: 1.5s interval)
- Promise.all for parallel data fetching
- useMemo for derived state

## Report Pipeline
- Jinja2 HTML template → stored via StorageProvider
- PDF: on-demand conversion via xhtml2pdf (pisa.CreatePDF)
- CSS variables inlined for xhtml2pdf compatibility
