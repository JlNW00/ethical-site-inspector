---
name: frontend-dev
description: Frontend development for EthicalSiteInspector React application — UI components, pages, tests
---

# Frontend Developer

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features involving:
- React/TypeScript components and pages
- UI styling (plain CSS in index.css)
- API client integration
- Frontend test suites
- Visual polish and animations

## Work Procedure

### 1. Understand the Feature
- Read the feature description, preconditions, expectedBehavior, and verificationSteps carefully
- Read `mission.md` and `AGENTS.md` for context and constraints
- Read `.factory/library/architecture.md` for frontend patterns
- Examine existing components in `frontend/src/` for styling conventions and patterns
- Check `frontend/src/api/types.ts` for existing type definitions
- Check `frontend/src/styles/index.css` for the CSS variable system and glass-morphism patterns

### 2. Write Tests First (TDD)
- Create or update test file(s) (*.test.tsx or *.test.ts) alongside source files
- Write failing tests using Vitest + React Testing Library
- Cover: rendering, user interactions, error states, loading states
- Run tests to confirm they fail: `cd frontend && npm test`

### 3. Implement
- Write components as functional React components with hooks
- TypeScript strict mode — no `any` types, proper interfaces
- Use the existing API client in `src/api/client.ts` for backend calls
- Add new types to `src/api/types.ts`
- CSS goes in `src/styles/index.css` — follow the existing dark glass-morphism theme:
  - Use CSS variables: --bg, --surface, --accent, --critical, --high, --medium, --low
  - backdrop-filter: blur() for glass effects
  - Rounded corners, subtle gradients
  - IBM Plex Sans (body), Space Grotesk (headings)
- Pattern categories in frontend MUST mirror backend taxonomy — import from a shared constants file
- Do NOT install new UI libraries (no MUI, no Chakra, no Tailwind)

### 4. Verify
- Run tests: `cd frontend && npm test`
- Run linter: `cd frontend && npm run lint`
- Run typecheck: `cd frontend && npx tsc -b`
- Run build: `cd frontend && npm run build`
- Fix ALL lint/type/build errors before committing

### 5. Manual Verification
- Start the dev server: `cd frontend && npm run dev -- --port 5173`
- Open the page in browser (via agent-browser or describe what you'd check)
- Verify visual appearance matches the glass-morphism theme
- Check responsive behavior at different viewport widths
- Kill the dev server before completing

### 6. Commit
- Stage all changed files
- Write a clear commit message
- Ensure no hardcoded URLs, secrets, or debug code in the diff

## Example Handoff

```json
{
  "salientSummary": "Built audit history page with status badges, filtering, search, rerun, and compare. Tests pass (8 new tests). Verified rendering with agent-browser showing proper glass-morphism styling and functional filters.",
  "whatWasImplemented": "Created frontend/src/pages/HistoryPage.tsx with audit list table, status badge component, URL search input, status filter tabs. Added GET /api/audits list endpoint to API client. Added HistoryPage route to App.tsx. Added rerun button (POST with same params) and compare selection (checkbox + compare button). Styled with glass-morphism theme matching existing pages.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {"command": "cd frontend && npm test", "exitCode": 0, "observation": "18 tests passed"},
      {"command": "cd frontend && npm run lint", "exitCode": 0, "observation": "No warnings"},
      {"command": "cd frontend && npx tsc -b", "exitCode": 0, "observation": "No errors"},
      {"command": "cd frontend && npm run build", "exitCode": 0, "observation": "Build succeeded"}
    ],
    "interactiveChecks": [
      {"action": "Opened history page at /history", "observed": "Table renders with 3 audits, status badges colored correctly (green=completed, red=failed)"},
      {"action": "Typed 'booking' in search field", "observed": "List filtered to show only booking.com audits"},
      {"action": "Selected 'completed' status filter", "observed": "Only completed audits shown"},
      {"action": "Clicked rerun on a completed audit", "observed": "New audit created, navigated to RunPage"}
    ]
  },
  "tests": {
    "added": [
      {"file": "frontend/src/pages/HistoryPage.test.tsx", "cases": [{"name": "renders audit list", "verifies": "history page displays audits from API"}, {"name": "filters by status", "verifies": "status filter updates displayed list"}, {"name": "search by URL", "verifies": "text search filters by target URL"}]}
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Backend API endpoint doesn't exist yet (needed for data fetching)
- Type definitions in types.ts are missing fields the feature needs
- CSS variable system needs new variables not in the existing theme
- Feature requires a new npm dependency that isn't installed
- Routing conflicts with existing pages
