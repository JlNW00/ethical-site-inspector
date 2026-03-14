# EthicalSiteInspector Deep Dive Report

Generated on March 12, 2026 after source review plus local smoke verification.

Repo state at review time:

- Local `main` matched `origin/main`
- `HEAD` and `origin/main` were both at `3c62806` (`Harden live cookie consent evidence capture`)

## Executive Summary

EthicalSiteInspector has a solid hackathon-grade scaffold, and the live path is materially stronger than the mock path:

- Clear full-stack separation between FastAPI backend and React/Vite frontend
- Good provider seams for browser automation, classification, and storage
- Clean report-generation path with HTML export
- UI builds successfully and the backend API surface is coherent
- Local live mode is configured correctly and real Booking.com audits already exist in the database
- Local readiness resolves to `effective_mode=live` with `PlaywrightAuditProvider` and `LiveNovaClassifierProvider`

The biggest problem is not the live integration. The biggest problem is that the default/demo path is currently unreliable. New mock audits can complete with zero findings, which collapses the no-secrets story in exactly the mode the README presents as the easiest demo route. There are also failure-mode issues that can leave an audit stuck in `running`, and the "seeded demo report" pointer is not actually stable.

## What I Verified Works

### Build and runtime checks

- Frontend production build succeeds with `npm run build`
- Backend modules compile cleanly with `python -m compileall`
- `GET /api/health` returns `200`
- `GET /api/readiness` returns `200`
- `GET /api/audits/{id}` works for an existing completed audit
- `GET /api/audits/{id}/findings` works
- `GET /api/audits/{id}/report` serves HTML successfully

### Verified local live-mode posture

- Local `.env` contains `USE_REAL_BROWSER=true`
- Local `.env` contains `NOVA_MODEL_ID=us.amazon.nova-premier-v1:0`
- `GET /api/readiness` reported:
  - `effective_mode=live`
  - `browser_provider=PlaywrightAuditProvider`
  - `classifier_provider=LiveNovaClassifierProvider`
- The local DB already contains completed Booking.com audits in `hybrid` and `live`
- The latest local Booking.com live audit completed successfully with:
  - mode `live`
  - status `completed`
  - trust score `26.0`
  - risk `critical`
  - 3 persisted findings
  - completed HTML report

### Architectural strengths

- `backend/app/services/provider_registry.py` cleanly swaps mock, hybrid, and live providers
- `backend/app/services/report_service.py` is a reasonable abstraction for report rendering and storage
- `backend/app/detectors/rule_engine.py` contains practical, easy-to-extend heuristics
- `frontend/src/pages/RunPage.tsx` and `frontend/src/pages/ReportPage.tsx` map well onto the demo story

## What Needs Fixed

### P1: Mock audits generate zero findings

Files:

- `backend/app/providers/browser.py:102`
- `backend/app/detectors/rule_engine.py:14`
- `backend/app/services/audit_orchestrator.py:245`

What happens:

- The mock provider returns observations without `scenario_state_found`, `action_count`, `observed_price_delta`, or other state metadata expected by the rule engine and metrics builder.
- The rule engine immediately exits when `scenario_state_found` is missing.
- Result: a newly created mock audit can finish with `0` findings, `100` trust score, empty scenario/persona breakdowns, and a misleading "No major trust risks" summary.

Verified behavior:

- I created a new mock audit through the API.
- It completed successfully.
- It produced `0` findings and a `100.0` trust score despite synthetic mock evidence containing obvious dark-pattern signals.

Impact:

- This breaks the main no-secrets-required demo path.
- The project currently undersells itself in the easiest bootstrap mode even though the live path is already demonstrating real value.

Recommendation:

- Make mock observations populate the same minimum metadata contract used by live observations:
  - `scenario_state_found`
  - `action_count`
  - `observed_price_delta`
  - `state_snapshots`
  - grounded `interacted_controls`

### P1: Audit failures after browser execution are never marked failed

File:

- `backend/app/services/audit_orchestrator.py:80`

What happens:

- Only the browser execution block is wrapped in `try/except`.
- If classification, metrics, report generation, DB writes, or event emission fail later, the thread dies and the audit remains `running`.

Impact:

- The run page can poll forever.
- Operators get no terminal failure event and no actionable error state.
- This is especially dangerous during live demos and production retries.

Recommendation:

- Wrap the rest of `run_audit()` in a top-level exception handler.
- On failure:
  - set `audit.status = "failed"`
  - persist an error summary
  - emit a terminal event with failure details

### P1: "Seeded demo report" is not actually a seeded demo

Files:

- `backend/app/services/seed_service.py:14`
- `backend/app/api/routes/health.py:35`

What happens:

- Both startup seeding and readiness use "latest completed audit with a report" as the demo ID.
- Any later user-created audit can replace the demo pointer, even if it is not the curated demo target.

Verified behavior:

- After creating a new audit, `seeded_demo_audit_id` pointed to that latest audit rather than a fixed demo record.

Impact:

- The "Open seeded demo report" button can open an arbitrary prior audit.
- Demo behavior becomes nondeterministic and can degrade after one bad run.
- In the current local state, readiness points to the latest mock `example.com` audit rather than the stronger completed Booking.com live audit.

Recommendation:

- Persist a dedicated seeded-demo audit keyed by target URL or a dedicated DB flag.
- Readiness should return that specific demo audit, not the latest completed audit globally.

### P2: First startup crashes on a fresh DB unless migrations were run first

Files:

- `backend/app/main.py:18`
- `backend/app/services/seed_service.py:13`

What happens:

- App startup calls `ensure_seeded_demo()` during lifespan.
- That function queries the `audits` table immediately.
- On a fresh SQLite path without `alembic upgrade head`, startup throws `sqlite3.OperationalError: no such table: audits`.

Impact:

- Local onboarding is brittle.
- A livestream demo on a fresh machine can fail before `/api/health` is reachable.

Recommendation:

- Either auto-create/apply schema in development startup or fail fast with a clearer bootstrap check and message.
- At minimum, guard seeding behind a schema-ready check.

### P2: There is no test suite covering the main audit flow

Observed state:

- No backend tests
- No frontend tests
- No CI configuration

Impact:

- Core regressions like the mock-audit issue are currently able to ship unnoticed.

Recommendation:

- Add a minimal test matrix first:
  - backend API smoke tests
  - mock audit end-to-end test asserting findings > 0
  - report route test
  - frontend render smoke for submit/run/report pages

## Other Risks and Gaps

- The project uses in-process threads for audit execution. That is acceptable for a hackathon but fragile for restarts, horizontal scaling, and long-running live audits.
- There is no auth or multi-user isolation.
- There is no retry/cancel/resume behavior for audits.
- There is no structured logging, tracing, or metrics export.
- The live browser heuristics are promising but still generic; detection quality will vary heavily across arbitrary sites.
- Cookie consent remains weaker than checkout/cancellation on some sites, especially in headless mode, even after the recent live-mode hardening.
- Hidden-cost detection is intentionally conservative and will miss cases unless a concrete delta is actually observed.
- Offer and hotel path selection is improved but still heuristic-driven rather than policy- or goal-aware.

## Features Worth Adding Next

### High-value product features

- Audit history dashboard with filtering, rerun, duplicate, and compare actions
- Side-by-side persona diff view showing path divergence, price deltas, and screenshot comparisons
- Finding triage workflow with statuses like `new`, `accepted`, `false positive`, `fixed`
- Export options beyond raw HTML: PDF, JSON, CSV
- Shareable report links with expiration

### Higher-quality evidence capture

- Full screenshot timeline or video replay per audit
- DOM snapshot diffing between key journey states
- Network request capture for hidden fees, tracking consent, and third-party pixels
- Accessibility signal capture alongside dark-pattern detection

### Stronger intelligence layer

- More specialized detectors per scenario instead of generic keyword matching
- Confidence scoring that distinguishes heuristic-only vs screenshot-supported findings
- Regulator-oriented mapping to FTC / GDPR / DSA / CPRA style policy categories
- False-positive suppression rules and site-specific tuning

### Operational maturity

- Real job queue instead of in-process threads
- Retry policy and terminal failure handling
- Rate limiting and target allow/block lists
- User auth and saved workspaces
- CI pipeline with smoke tests on pull requests

## Best Immediate Build Plan

If the goal is to make this strong enough for a Factory livestream build session, I would do these in order:

1. Fix mock audit metadata so seeded/demo audits always produce meaningful findings.
2. Add terminal `failed` state handling in the orchestrator.
3. Make the seeded demo deterministic and point it at a known-good audit story.
4. Add one backend smoke test for "create mock audit -> findings > 0 -> report exists".
5. Improve cookie-consent capture reliability on live sites in headless mode.
6. Add an audit history page and rerun action.

That sequence gives you the fastest path to a stable demo plus a believable roadmap.

## Commands Run During Review

- `npm run build`
- `python -m compileall backend/app`
- FastAPI smoke requests via `fastapi.testclient`
- Fresh-DB startup check against a temporary SQLite file
