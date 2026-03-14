# Cross-Area Validation Assertions

> Assertions covering flows that span multiple new features or connect new features
> to existing ones in EthicalSiteInspector.
>
> New features under validation:
> 1. Video Replay — `record_video` during audits, S3 storage, video player on ReportPage
> 2. Benchmark Mode — multi-URL (2–5) comparative auditing, BenchmarkPage with side-by-side view
> 3. Regulatory PDF — formal compliance report per regulation (FTC / GDPR / DSA / CPRA)
> 4. AWS Deployment — CloudFormation, systemd, nginx, mypy fixes

---

### VAL-CROSS-001: All new features reachable through normal navigation

**Behavioral description:**
Starting from `SubmitPage` (`/`), a user must be able to reach every new feature surface—Video Replay player, BenchmarkPage, and Regulatory PDF download—using only links, buttons, and form submissions rendered by the app (no manual URL entry). The navigation graph must include:
- A path from the global nav or SubmitPage to launch a benchmark audit.
- A path from a completed audit's ReportPage to the video replay player.
- A path from a completed audit's ReportPage (or a new regulatory section) to download a regulation-specific PDF.

**Pass condition:** An automated or manual walkthrough from `/` can click through to each feature surface without typing a URL. Every new route registered in `App.tsx` is the `href`/`to` target of at least one `<Link>` or `<a>` element rendered in the existing page tree.

**Fail condition:** Any new route is only reachable by direct URL entry (orphan route).

**Evidence:** Screenshot or DOM snapshot of the navigation element that links to each new feature; route coverage matrix mapping every new `<Route>` in `App.tsx` to at least one in-app link source.

---

### VAL-CROSS-002: Full single-URL audit flow with video and regulatory PDF

**Behavioral description:**
The existing end-to-end flow—`SubmitPage` → `RunPage` → `ReportPage`—must continue to work and now additionally surface video replay and regulatory PDF capabilities:
1. User submits a single URL on SubmitPage; navigates to RunPage.
2. RunPage shows audit progress. If video recording is active, a visual indicator (e.g., "Recording video…" event or progress badge) appears in the activity timeline or run-state section.
3. Upon completion, user clicks "Open report" → arrives at ReportPage.
4. ReportPage displays the video replay player (or a clear "Video unavailable" fallback when no video was recorded).
5. ReportPage offers a "Download Regulatory PDF" control (per-regulation or consolidated) alongside the existing "Download PDF" button.

**Pass condition:** Starting from `/`, a completed audit produces a ReportPage that renders both the video player area and at least one regulatory PDF download action without console errors or 404s.

**Fail condition:** ReportPage is missing either the video section or the regulatory PDF control; or the existing "Download PDF" button is removed/broken.

**Evidence:** Network log showing successful `GET /api/audits/{id}/report/pdf/regulatory?regulation=FTC` (or equivalent) and `GET /api/audits/{id}/video`; DOM snapshot of ReportPage confirming both sections rendered.

---

### VAL-CROSS-003: Benchmark audit results include per-URL video recordings

**Behavioral description:**
When a user starts a benchmark audit (2–5 URLs) on BenchmarkPage, each constituent single-URL audit should independently record video. On the BenchmarkPage results view (side-by-side comparison), each URL column must include either:
- An inline video player thumbnail that expands on click, or
- A link to the individual audit's ReportPage where video can be viewed.

**Pass condition:** After a benchmark audit with N URLs completes, the benchmark results view provides access to exactly N video recordings (one per URL). Clicking each opens a playable video or navigates to a ReportPage with the video player.

**Fail condition:** Any constituent audit's video is missing, inaccessible, or the benchmark view has no way to access videos.

**Evidence:** API responses for each constituent audit confirming `video_url` is populated; screenshot of BenchmarkPage showing video access points for all N URLs.

---

### VAL-CROSS-004: Regulatory PDF references video evidence when available

**Behavioral description:**
When a regulatory PDF (e.g., FTC compliance report) is generated for an audit that also has video recordings, the PDF document must reference the video evidence. This may take the form of:
- A "Video Evidence" section listing video URLs or S3 keys.
- Timestamps in the PDF findings that cross-reference moments in the video.
- At minimum, a statement such as "Video recording available at: [URL]" in the evidence section.

**Pass condition:** Generated regulatory PDF for an audit with `video_url != null` contains at least one reference to the video recording (URL, filename, or timestamp reference). The PDF remains valid (no broken references) when video is absent.

**Fail condition:** Regulatory PDF for a video-enabled audit makes no mention of video evidence; or the PDF breaks (rendering error, missing template variable) when video is absent.

**Evidence:** Extracted text content from regulatory PDF showing video reference; a second PDF generated for a non-video audit confirming graceful degradation.

---

### VAL-CROSS-005: Benchmark audits appear in HistoryPage with correct metadata

**Behavioral description:**
After completing a benchmark audit, it must appear in HistoryPage alongside regular single-URL audits. The history entry must:
1. Be visually distinguishable as a benchmark (e.g., badge, icon, or "Benchmark" label).
2. Show the number of URLs compared (e.g., "3 URLs").
3. Clicking the row navigates to the BenchmarkPage results view (not a single-audit ReportPage).
4. The "Back to History" link on BenchmarkPage navigates back to `/history`.

**Pass condition:** HistoryPage lists benchmark audits; clicking one navigates to BenchmarkPage; "Back to History" returns the user to `/history`. Status filter ("completed", "running", etc.) correctly includes/excludes benchmark audits.

**Fail condition:** Benchmark audits are absent from history; clicking a benchmark row navigates to a single-URL ReportPage; or filters break when benchmarks are present.

**Evidence:** Screenshot of HistoryPage showing benchmark entry; navigation trace (URL bar) confirming BenchmarkPage → HistoryPage round-trip; API response from `GET /api/audits` showing benchmark audit with distinguishing metadata.

---

### VAL-CROSS-006: Existing single-URL audit and PDF export still work unchanged

**Behavioral description:**
The introduction of Video Replay, Benchmark Mode, and Regulatory PDF must not regress the existing single-URL audit flow or the existing HTML/PDF export:
1. `POST /api/audits` with a single `target_url` still creates and completes an audit.
2. `GET /api/audits/{id}/report` still returns the HTML report.
3. `GET /api/audits/{id}/report/pdf` still returns a valid `application/pdf` response with `Content-Disposition` header.
4. ReportPage still renders: trust score, findings, persona comparison, scenario breakdown, screenshot timeline, "Download PDF" button, and "Compare Personas" link.
5. HistoryPage, ComparePage, and PersonaDiffPage work as before.

**Pass condition:** All existing backend tests in `test_pdf_export.py`, `test_regulatory_mapping.py`, and frontend tests in `ReportPage.test.tsx`, `HistoryPage.test.tsx`, `ComparePage.test.tsx`, `PersonaDiffPage.test.tsx` continue to pass. Manual walkthrough of single-URL flow produces identical behavior to pre-feature baseline.

**Fail condition:** Any existing test fails; any existing button/link/section disappears from ReportPage; PDF endpoint returns non-PDF content or 500.

**Evidence:** CI test results (all green); `git diff` of existing page components confirming no removals of existing elements; HTTP response headers from PDF endpoint.

---

### VAL-CROSS-007: Benchmark + Regulatory PDF — per-URL regulatory PDF download

**Behavioral description:**
From the BenchmarkPage results view, a user must be able to download a regulation-specific PDF for any individual URL within the benchmark. The flow is:
1. User views completed benchmark results on BenchmarkPage.
2. For each URL column, a "Regulatory Report" dropdown or button set allows selecting a regulation (FTC / GDPR / DSA / CPRA).
3. Clicking triggers download of the regulatory PDF scoped to that single URL's audit findings.

Alternatively, if BenchmarkPage links to individual ReportPages, those ReportPages must offer the regulatory PDF download (covered by VAL-CROSS-002), and the navigation back to BenchmarkPage must be seamless.

**Pass condition:** Starting from BenchmarkPage, user can obtain a regulatory PDF for each individual URL's audit within ≤ 2 clicks. The PDF content is scoped to findings from that specific URL only (not the entire benchmark).

**Fail condition:** No path exists from BenchmarkPage to a per-URL regulatory PDF; or the generated PDF contains findings from other URLs in the benchmark.

**Evidence:** Downloaded PDF content confirming `target_url` matches the selected URL; navigation trace showing ≤ 2 clicks from BenchmarkPage to PDF download.

---

### VAL-CROSS-008: First-visit discoverability — new user can find all features

**Behavioral description:**
A first-time user landing on `SubmitPage` (`/`) with an empty database (no seeded demo audit, `readiness.seeded_demo_audit_id === null`) should be able to discover all features:
1. The SubmitPage hero or form section makes benchmark mode discoverable (e.g., "Add more URLs" or "Benchmark mode" toggle).
2. After completing any audit, ReportPage surfaces video replay and regulatory PDF as visible sections (even if showing "not available" placeholders).
3. The global nav (`Layout.tsx`) includes a link or entry point for BenchmarkPage (or benchmark is integrated into SubmitPage).
4. No feature requires prior knowledge of a direct URL to access.

**Pass condition:** A usability trace of a new user's first session (submit → run → report → history) encounters UI affordances for all four feature areas. Each affordance is either actionable or shows a clear explanation of prerequisites.

**Fail condition:** Any feature is completely hidden from the first-visit flow; or a feature surface shows a blank/broken state with no explanatory text.

**Evidence:** Annotated screenshot sequence of the first-visit flow highlighting each feature discovery point; list of all UI affordances found per feature.

---

### VAL-CROSS-009: Video progress indicator visible during RunPage polling

**Behavioral description:**
When an audit is running with video recording enabled, the RunPage activity timeline (which polls `GET /api/audits/{id}` every 1.5s) must surface video-related progress. This connects the Video Replay feature to the existing RunPage infrastructure:
1. Audit events should include video-recording milestones (e.g., `phase: "video"`, `message: "Recording browser session…"`).
2. The RunPage "Evidence captured" metric or a new "Video status" metric should reflect recording state.
3. After completion, a link or indicator on RunPage should confirm video is available before the user navigates to ReportPage.

**Pass condition:** During a video-enabled audit run, at least one event with video-related content appears in the RunPage timeline. After completion, the "Open report" button area includes a note or badge indicating video is ready.

**Fail condition:** RunPage shows zero video-related events during a video-enabled audit; user has no indication that video was recorded until they reach ReportPage.

**Evidence:** Captured `GET /api/audits/{id}` response showing events with `phase: "video"` or equivalent; DOM snapshot of RunPage during and after a video-enabled run.

---

### VAL-CROSS-010: HistoryPage compare flow works with mixed audit types

**Behavioral description:**
HistoryPage allows selecting 2 audits and clicking "Compare" to navigate to ComparePage (`/compare?a={id}&b={id}`). With Benchmark Mode introduced, the compare flow must handle:
1. Comparing two single-URL audits (existing behavior, must not regress).
2. Comparing a single-URL audit with a benchmark audit (should show a meaningful comparison or a clear "incompatible" message).
3. Benchmark audits should not be selectable for the existing 2-audit compare if the compare flow is not designed for multi-URL entities (guard rail).

**Pass condition:** Selecting two single-URL audits and clicking "Compare" navigates to ComparePage and renders correctly. If a benchmark audit is selected alongside a single-URL audit, the system either produces a useful comparison or shows a clear, non-error explanation of incompatibility. No unhandled exceptions.

**Fail condition:** ComparePage crashes or shows undefined data when a benchmark audit is included; or benchmark audits are silently excluded from HistoryPage (violating VAL-CROSS-005).

**Evidence:** ComparePage screenshot for single-vs-single comparison; ComparePage or error-state screenshot for single-vs-benchmark comparison; console log confirming no unhandled errors.
