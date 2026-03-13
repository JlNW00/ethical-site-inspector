# Architecture

Architectural decisions, patterns, and constraints.

---

## Layered Architecture
Routes → AuditOrchestrator → Providers (browser/classifier/storage)

## Provider Pattern (Strategy)
All providers implement ABCs:
- `BrowserAuditProvider` — browser automation (NovaActAuditProvider for live mode)
- `ClassifierProvider` — AI classification (LiveNovaClassifierProvider for live mode)
- `StorageProvider` — file storage (LocalStorageProvider for dev)

Provider selection via `backend/app/services/provider_registry.py` based on mode config.

## Audit Modes
- `mock` — simulated data, no external calls (NOT a priority for this mission)
- `hybrid` — real browser + mock AI (NOT a priority for this mission)
- `live` — Nova Act browser + Nova Bedrock classification (THE priority)

## Audit Flow
1. POST /api/audits creates audit record, starts background thread
2. AuditOrchestrator.run_audit():
   a. Browser provider navigates site per scenario/persona combinations
   b. Rule engine detects patterns from observations
   c. Classifier provider enriches findings with AI analysis
   d. Metrics computed, report generated, status updated
3. Frontend polls GET /api/audits/{id} for progress events
4. On completion, report available at GET /api/audits/{id}/report

## Taxonomy (Single Source of Truth)
`backend/app/core/taxonomy.py` defines:
- Pattern categories: manipulative_design, deceptive_content, coercive_flow, obstruction, sneaking, social_proof_manipulation
- Scenarios: cookie_consent, subscription_cancellation, checkout_flow, account_deletion, newsletter_signup, pricing_comparison
- Personas: privacy_sensitive, cost_sensitive, exit_intent
- Severity levels, regulatory mappings

## Database
3 tables: audits, findings, audit_events
- Audit → many Findings (cascade delete)
- Audit → many AuditEvents (cascade delete)

## Frontend
- React 18 + Vite + TypeScript (strict)
- Plain CSS (dark glass-morphism theme)
- Polling-based real-time updates (no WebSocket)
- Pages: SubmitPage, RunPage, ReportPage + new History/Diff pages
