---
name: frontend-dev
description: Frontend development for EthicalSiteInspector React application — pages, components, API client, tests
---

# Frontend Developer

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Use for features that involve:
- React pages and components
- TypeScript types and API client methods
- CSS styling (dark glassmorphism theme)
- Frontend routing (App.tsx)
- Vitest test coverage
- UI/UX integration with backend APIs

## Work Procedure

### 1. Understand the Feature
- Read the feature description, preconditions, expectedBehavior, and verificationSteps from features.json
- Read `AGENTS.md` for coding conventions and boundaries
- Read `.factory/library/architecture.md` for frontend patterns
- Check the existing page/component you're extending (read the full file)
- Check `src/api/types.ts` and `src/api/client.ts` for current API types

### 2. Write Tests First (TDD Red Phase)
- Create or update test file: `src/pages/<Page>.test.tsx` or `src/components/<Component>.test.tsx`
- Write test cases covering ALL expectedBehavior items
- Mock the API client: `vi.mock("../api/client")` or `vi.mock("../../api/client")`
- Use `createMockAudit()` and `createMockFinding()` helpers with overrides for new fields
- Wrap components in `MemoryRouter` with appropriate routes
- Run tests to confirm they FAIL: `cd frontend && npx vitest run src/pages/<Page>.test.tsx`
- Record the failing test output

### 3. Implement (TDD Green Phase)
- Create/modify files in this order:
  1. **Types** (`src/api/types.ts`) — Add new TypeScript interfaces/types
  2. **API Client** (`src/api/client.ts`) — Add new API methods
  3. **Components** (`src/components/`) — New reusable components
  4. **Pages** (`src/pages/`) — New or modified pages
  5. **Routes** (`src/App.tsx`) — Register new routes
  6. **Styles** (`src/styles/index.css`) — Add CSS classes following glassmorphism theme
- Follow existing patterns:
  - Pages: export named function, wrap in `<Layout>`, use `.hero-panel` and `.content-panel`
  - Data fetching: `useState` + `useEffect` with cancellation (`let cancelled = false`)
  - Parallel fetches: `Promise.all([api.method1(), api.method2()])`
  - Derived state: `useMemo` for computed values

### 4. Verify Tests Pass (TDD Green Confirmation)
- Run your new tests: `cd frontend && npx vitest run src/pages/<Page>.test.tsx`
- Run the FULL test suite: `cd frontend && npx vitest run`
- ALL tests must pass (both new and existing)

### 5. TypeScript and Lint
- Run TypeScript: `cd frontend && npx tsc -b`
- Run ESLint: `cd frontend && npm run lint`
- Fix any issues introduced by your changes
- Zero tolerance for TypeScript errors

### 6. Manual Verification with agent-browser
- Start both servers (backend on 8000, frontend on 5173)
- Use agent-browser to navigate to the page you built/modified
- Verify:
  - Page loads without console errors
  - All expected UI elements are visible
  - Interactive elements work (buttons, toggles, forms)
  - Data from API renders correctly
  - Loading and error states display properly
  - Navigation links work
- Take screenshots of key states
- Stop servers after testing
- Record each check with action and observation

### 7. Update Shared Knowledge
- If you discover something other workers need to know, update `.factory/library/architecture.md`

## Example Handoff

```json
{
  "salientSummary": "Built BenchmarkPage with progress tracking, trust score comparison, scenario breakdown grid, and unified summary. Added /benchmarks/:id route to App.tsx. Added getBenchmark() and getBenchmarks() to API client. 8 tests covering loading, error, comparison view, navigation. All 140 tests pass, tsc clean, ESLint clean. Verified with agent-browser: page loads, polls for updates, renders comparison grid correctly.",
  "whatWasImplemented": "New BenchmarkPage.tsx with 4 sections: progress tracking (per-URL ProgressMeter), trust score comparison (ranked cards with delta), scenario breakdown (grid table), and unified summary (generated text). New types: Benchmark, BenchmarkAudit in types.ts. New API methods: getBenchmark(), getBenchmarks(). New route /benchmarks/:id in App.tsx. ~200 lines of new CSS in index.css following glassmorphism theme.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "cd frontend && npx vitest run src/pages/BenchmarkPage.test.tsx",
        "exitCode": 0,
        "observation": "8 tests passed: renders loading state, renders error state, renders comparison view with trust scores ranked, renders scenario grid with correct cell values, renders summary with highest/lowest URL, navigation to individual reports, back link to benchmarks"
      },
      {
        "command": "cd frontend && npx vitest run",
        "exitCode": 0,
        "observation": "140 tests passed across 12 files. No regressions."
      },
      {
        "command": "cd frontend && npx tsc -b",
        "exitCode": 0,
        "observation": "No TypeScript errors"
      },
      {
        "command": "cd frontend && npm run lint",
        "exitCode": 0,
        "observation": "No ESLint errors"
      }
    ],
    "interactiveChecks": [
      {
        "action": "Navigate to /benchmarks/{id} for a completed benchmark with 3 URLs",
        "observed": "Page loads with trust score comparison showing 3 URL cards ranked by score. Delta indicator shows difference between best (78) and worst (45). Scenario grid renders correctly with finding counts. Summary mentions highest and lowest scoring URLs by name."
      },
      {
        "action": "Click 'View Report' on first URL card",
        "observed": "Navigated to /audits/{id}/report for that URL's audit. ReportPage loads correctly with back breadcrumb showing 'Back to Benchmark'."
      }
    ]
  },
  "tests": {
    "added": [
      {
        "file": "src/pages/BenchmarkPage.test.tsx",
        "cases": [
          {"name": "renders loading state while fetching", "verifies": "Shows spinner/skeleton before data loads"},
          {"name": "renders trust score comparison ranked by score", "verifies": "URLs ordered highest to lowest trust score"},
          {"name": "renders scenario breakdown grid", "verifies": "Grid shows finding counts per scenario per URL"},
          {"name": "renders unified summary with key insights", "verifies": "Summary names highest/lowest URL and mentions patterns"},
          {"name": "navigates to individual audit report", "verifies": "View Report link goes to /audits/{id}/report"}
        ]
      }
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Backend API endpoint doesn't exist yet or returns unexpected schema
- Required API types are missing or incorrect compared to actual backend response
- Existing component needs structural changes that would break other pages
- CSS theme system needs new design tokens not covered by existing variables
- You discover that the feature scope is significantly larger than described
