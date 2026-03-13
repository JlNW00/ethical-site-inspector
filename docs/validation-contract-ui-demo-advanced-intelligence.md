# Validation Contract — UI Demo & Advanced Intelligence

> **Project:** EthicalSiteInspector  
> **Areas:** UI Demo (VAL-UI-xxx), Advanced Intelligence (VAL-ADV-xxx)  
> **Drafted:** 2026-03-12  
> **Baseline:** Current frontend routes: `/` (SubmitPage), `/audits/:id/run` (RunPage), `/audits/:id/report` (ReportPage)

---

## Area 1 — UI Demo (VAL-UI-xxx)

### VAL-UI-001 · Audit History Dashboard — List Display

**Title:** History page lists all past audits with status badges, trust scores, and timestamps.

**Behavioral description:**  
When the user navigates to the audit history page, a table or card list renders every previously created audit. Each entry MUST display:
- The target URL (or hostname)
- A status badge (`queued`, `running`, `completed`, `failed`) with visually distinct styling per status
- The trust score (numeric, e.g. `72 / 100`) or `--` if not yet computed
- A formatted timestamp (`created_at`)

**Pass condition:** The history page renders ≥1 audit row. Each row contains a non-empty target URL string, a status badge element whose text matches one of the four `AuditStatus` values, a trust score display, and a human-readable timestamp.  
**Fail condition:** The page is blank, any row is missing one of the four required data points, or status badges are rendered as raw text without visual distinction.

**Evidence requirements:**
- Screenshot of the history page with ≥2 audits visible
- DOM snapshot confirming status badge CSS class or data attribute per row
- API response from `GET /api/audits` (or equivalent list endpoint) showing the data

---

### VAL-UI-002 · Audit History Dashboard — Filter and Search

**Title:** Users can filter the history list by status and search by URL.

**Behavioral description:**  
The history page provides:
1. A status filter control (dropdown, toggle group, or tabs) that limits visible audits to those matching the selected status.
2. A text search input that filters audits by target URL substring match (case-insensitive).

Applying a filter updates the displayed list in real time (no full page reload). Clearing all filters restores the full list.

**Pass condition:** Selecting a status filter shows only audits with that status. Typing a partial URL in the search field shows only matching audits. Clearing both controls restores the complete list. Zero-result states display a meaningful empty message.  
**Fail condition:** Filters have no effect on the displayed list, search is case-sensitive when it should not be, or clearing filters does not restore the full list.

**Evidence requirements:**
- Screenshot before filtering, after status filter applied, and after search text entered
- Console log or network tab confirming no full page reload on filter change (or client-side filtering)

---

### VAL-UI-003 · Audit History Dashboard — Click to View Report

**Title:** Clicking an audit in the history list navigates to its report page.

**Behavioral description:**  
Each audit entry in the history list is clickable (row click, link, or explicit button). Clicking navigates the browser to `/audits/{auditId}/report`. The ReportPage loads and displays data for that specific audit.

**Pass condition:** Click event on an audit row triggers navigation to the correct `/audits/{auditId}/report` URL. The ReportPage renders with the matching audit's target URL, trust score, and findings.  
**Fail condition:** Clicking does nothing, navigates to the wrong audit, or produces a 404/error.

**Evidence requirements:**
- Screen recording or sequential screenshots showing the click and resulting navigation
- Browser URL bar showing the correct `/audits/{id}/report` path

---

### VAL-UI-004 · Audit History Dashboard — Rerun Audit

**Title:** Users can rerun a completed audit with the same parameters.

**Behavioral description:**  
Each completed audit in the history list (or on its report page) has a "Rerun" button/action. Clicking it creates a new audit via `POST /api/audits` using the same `target_url`, `scenarios`, and `personas` as the original. The user is then navigated to the new audit's RunPage (`/audits/{newAuditId}/run`).

**Pass condition:** Clicking rerun triggers a `POST /api/audits` with parameters matching the original audit. A new audit ID is returned. The browser navigates to `/audits/{newId}/run`. The new audit appears in the history list as a separate entry.  
**Fail condition:** Rerun button is absent, the POST uses different parameters than the original, or the user is not navigated to the new run.

**Evidence requirements:**
- Network request log showing the POST body with matching `target_url`, `scenarios`, `personas`
- Screenshot of the new RunPage after rerun

---

### VAL-UI-005 · Audit History Dashboard — Compare Audits

**Title:** Users can select two audits and compare their results side by side.

**Behavioral description:**  
The history page allows the user to select exactly two audits (via checkboxes, multi-select, or a compare action). A "Compare" button becomes enabled when two are selected. Clicking it navigates to a comparison view showing the two audits' trust scores, risk levels, finding counts, and key metric deltas.

**Pass condition:** The compare button is disabled when fewer or more than two audits are selected. When two are selected and compare is clicked, a comparison view loads showing both audits' metrics side by side with computed deltas (e.g., trust score difference).  
**Fail condition:** Compare button is always enabled/disabled regardless of selection, or the comparison view does not show both audits' data.

**Evidence requirements:**
- Screenshots of selection state (0, 1, 2 selected) showing button enable/disable
- Screenshot of the comparison view with both audits' data visible

---

### VAL-UI-006 · Persona Diff View — Side-by-Side Layout

**Title:** Persona diff view shows side-by-side comparison of persona experiences on the same site.

**Behavioral description:**  
A dedicated diff view (or modal/panel) renders a side-by-side comparison of how different personas experienced the same audit. For each persona pair, the view shows:
- Path divergence: the UI action sequences taken by each persona
- Price deltas: any pricing differences observed between personas
- Different UI treatment: different button labels, checkbox states, or UI elements shown

**Pass condition:** The diff view renders at least two persona columns. Each column shows the persona name, the observed action path, price points (if applicable), and matched UI controls. Differences between personas are visually highlighted (color, icon, or annotation).  
**Fail condition:** Only one persona is shown, paths are not displayed, or differences are not visually distinguished from shared data.

**Evidence requirements:**
- Screenshot of the diff view with ≥2 personas shown side by side
- DOM inspection confirming diff-highlight CSS classes or elements
- The underlying data (persona_comparison metrics, finding evidence_payload) used to populate the view

---

### VAL-UI-007 · Enhanced Report Page — Screenshot Timeline

**Title:** Report page shows a screenshot timeline with evidence at each journey step.

**Behavioral description:**  
The report page includes a chronological timeline of screenshots captured during the audit. Each screenshot entry shows:
- The screenshot image (thumbnail, expandable on click)
- A caption indicating the scenario, persona, and step context
- Chronological ordering matching the audit event sequence

**Pass condition:** The timeline renders ≥1 screenshot per scenario-persona combination that produced evidence. Images load successfully (no broken image icons). Captions include scenario and persona context. Timeline is ordered chronologically.  
**Fail condition:** No timeline section exists, images fail to load, captions are missing, or ordering is random/unsorted.

**Evidence requirements:**
- Screenshot of the timeline section on the report page
- Network requests showing successful image loads from `screenshot_urls`
- Comparison of timeline order with `AuditEvent` `created_at` timestamps

---

### VAL-UI-008 · Enhanced Report Page — Findings Grouped by Scenario

**Title:** Findings on the report page are grouped by scenario with persona sub-groups.

**Behavioral description:**  
The current report page groups findings by scenario (e.g., Cookie Consent, Checkout Flow) and then by persona within each scenario. Each group has a visible heading with the scenario name (titleized). Within each scenario group, findings are further sub-grouped by persona with persona name labels.

**Pass condition:** Findings are rendered in a nested group structure: scenario heading → persona label → finding cards. The grouping matches the `finding.scenario` and `finding.persona` fields. Empty groups are not rendered.  
**Fail condition:** Findings are in a flat list without grouping, grouping headings are missing, or findings appear under the wrong scenario/persona.

**Evidence requirements:**
- Screenshot of the findings section showing at least two scenario groups
- DOM inspection confirming the nesting structure (scenario container → persona container → FindingCard)

*Note: This behavior already exists in the current ReportPage via `groupedFindings`. This assertion confirms it remains intact.*

---

### VAL-UI-009 · PDF Export

**Title:** Users can download a PDF version of the audit report.

**Behavioral description:**  
The report page includes a "Download PDF" button (or equivalent action). Clicking it either:
- Triggers a client-side PDF generation (e.g., via html2pdf, jsPDF, or print-to-PDF) and initiates a file download, OR
- Requests a server-generated PDF from the backend and initiates a file download.

The resulting PDF contains: the trust score, risk level, executive summary, and at least the finding titles and severity levels.

**Pass condition:** Clicking the PDF button initiates a file download. The downloaded file is a valid PDF (opens in a PDF reader). The PDF contains the audit's trust score, risk level, and finding information.  
**Fail condition:** No download occurs, the file is corrupt/empty, or the PDF is missing the trust score or findings.

**Evidence requirements:**
- Screenshot showing the PDF download button on the report page
- The downloaded PDF file itself
- Verification that the PDF contains trust score and at least one finding title (manual or automated check)

---

### VAL-UI-010 · Navigation — All Pages Reachable

**Title:** All pages are reachable via in-app navigation (not just direct URL entry).

**Behavioral description:**  
The application provides a persistent navigation element (navbar, sidebar, or breadcrumbs) that allows users to navigate between:
1. Home / Submit page (`/`)
2. Audit history page (new)
3. Individual audit run page (`/audits/:id/run`) — via history or submit flow
4. Individual audit report page (`/audits/:id/report`) — via run page or history
5. Persona diff view — via report page or history

Every page includes a way to return to the home page and access the history.

**Pass condition:** Starting from the home page, the user can reach every other page through clickable UI elements without manually editing the URL. Every page has a navigation link back to home and to the history list.  
**Fail condition:** Any page is only reachable via direct URL entry. Any page lacks a way to navigate to another section.

**Evidence requirements:**
- Sequential screenshots or screen recording showing navigation from home → history → report → diff view → home
- DOM inspection confirming navigation links/elements exist on each page

---

### VAL-UI-011 · Error States — Failed Audits

**Title:** Failed audits display proper error messages with clear visual treatment.

**Behavioral description:**  
When an audit has `status: "failed"`:
- The RunPage shows a clear error state (not just frozen progress) with an error message
- The history page shows a `failed` status badge with distinct styling (e.g., red/critical color)
- The ReportPage (if navigated to) shows a meaningful message like "This audit failed" rather than empty content

**Pass condition:** A failed audit displays a visually distinct error state on RunPage (error message visible, progress indicator stops or turns red). The history page shows a failed badge. The ReportPage displays an explanatory message.  
**Fail condition:** Failed audits look identical to running or queued audits, no error message is shown, or the page renders blank/broken.

**Evidence requirements:**
- Screenshot of a failed audit on the RunPage showing error state
- Screenshot of the history page showing the failed status badge
- Screenshot of the ReportPage for a failed audit showing the explanatory message

---

### VAL-UI-012 · Loading States

**Title:** All data-fetching pages show loading indicators during data retrieval.

**Behavioral description:**  
Every page that fetches data from the API (`SubmitPage` readiness check, `RunPage` polling, `ReportPage` load, history page list) shows a visible loading indicator (spinner, skeleton, shimmer, or text placeholder like "Loading…") while data is being fetched. The loading state is replaced by content once data arrives.

**Pass condition:** On initial page load (with simulated slow network via DevTools throttling), a loading indicator is visible before content renders. The indicator disappears once data loads.  
**Fail condition:** Pages show blank/empty content during loading with no visual indicator, or loading indicators persist after data has loaded.

**Evidence requirements:**
- Screenshots captured during loading state (network throttled) and after data loads for at least 2 pages
- DevTools network timeline showing the delay and corresponding UI state

---

### VAL-UI-013 · Visual Polish — Animations and Transitions

**Title:** The UI includes smooth animations and transitions for a professional demo appearance.

**Behavioral description:**  
The application applies CSS transitions or animations for:
1. Page transitions or content appearance (fade-in, slide-in)
2. Progress meter changes on the RunPage (smooth width transition)
3. Hover effects on interactive elements (buttons, cards)
4. Status changes (e.g., running → completed badge transition)

**Pass condition:** At least 3 of the 4 animation categories are present. Transitions are smooth (not jarring or instant). Animation durations are between 150ms and 600ms (professional feel, not sluggish).  
**Fail condition:** No animations exist anywhere, or animations are longer than 1s causing the UI to feel slow.

**Evidence requirements:**
- Screen recording showing at least 3 distinct animation/transition effects
- CSS inspection showing `transition` or `@keyframes` rules

---

### VAL-UI-014 · RunPage — Live Progress Updates

**Title:** The RunPage polls for updates and renders progress in real time.

**Behavioral description:**  
When an audit is running, the RunPage polls `GET /api/audits/{id}` at regular intervals (~1.5s based on current implementation). Each poll updates:
- The progress percentage and progress meter
- The activity timeline with new events
- The evidence preview grid with new screenshots
- The metric cards (current focus, evidence count)

When the audit completes, polling stops and a "Open report" link appears.

**Pass condition:** The progress meter advances as the audit progresses. New timeline events appear without page refresh. Evidence thumbnails populate as screenshots are captured. The "Open report" link appears when `status === "completed"`.  
**Fail condition:** Progress is stuck, timeline never updates, or the report link never appears after completion.

**Evidence requirements:**
- Sequential screenshots or recording showing progress advancing from <50% to 100%
- Network tab showing periodic GET requests to the audit endpoint
- Screenshot showing the "Open report" link after completion

*Note: This behavior already exists in the current RunPage. This assertion confirms it remains intact and functions correctly.*

---

## Area 2 — Advanced Intelligence (VAL-ADV-xxx)

### VAL-ADV-001 · Regulatory Mapping — Finding Data

**Title:** Each finding includes a `regulatory_categories` field listing potentially violated regulations.

**Behavioral description:**  
The `Finding` object returned by `GET /api/audits/{id}/findings` includes a `regulatory_categories` field (array of strings). Each string represents a regulation the finding potentially violates. Valid regulation identifiers include: `FTC` (Federal Trade Commission Act), `GDPR` (General Data Protection Regulation), `DSA` (Digital Services Act), `CPRA` (California Privacy Rights Act). A finding MAY have zero or more regulatory categories.

**Pass condition:** The API response for findings includes a `regulatory_categories` field on every finding object. The field is an array of strings. At least one finding in a completed audit has ≥1 regulatory category. All values in the array are from the recognized set (`FTC`, `GDPR`, `DSA`, `CPRA`) or are clearly labeled custom regulation names.  
**Fail condition:** The `regulatory_categories` field is absent from the Finding schema, is not an array, or all findings in a completed audit have empty arrays.

**Evidence requirements:**
- Raw API JSON response from `GET /api/audits/{id}/findings` showing `regulatory_categories` on ≥2 findings
- Backend schema definition (Pydantic model and SQLAlchemy column) showing the field declaration
- At least one finding with `regulatory_categories: ["FTC", "GDPR"]` or similar multi-regulation match

---

### VAL-ADV-002 · Regulatory Mapping — UI Display

**Title:** The report page displays regulatory badges per finding.

**Behavioral description:**  
Each `FindingCard` component on the ReportPage renders the `regulatory_categories` as visual badge elements (pills, tags, or chips). Each badge displays the regulation name (e.g., "GDPR", "FTC"). Badges are styled distinctly from other pills (e.g., different color, icon, or border) to make regulatory context immediately recognizable.

**Pass condition:** FindingCards with non-empty `regulatory_categories` display one badge per regulation. Badges are visually distinct from severity and pattern_family pills. Findings with no regulatory categories render no regulatory badges (no empty/blank badges).  
**Fail condition:** Regulatory categories are in the API data but not rendered in the UI, badges are indistinguishable from other pills, or empty regulatory arrays render phantom badges.

**Evidence requirements:**
- Screenshot of a FindingCard showing regulatory badges (e.g., "GDPR", "FTC")
- DOM inspection confirming badge elements with correct text content
- Screenshot of a FindingCard without regulatory categories confirming no regulatory badges appear

---

### VAL-ADV-003 · Confidence Scoring — Data Range and Evidence Type

**Title:** Each finding has a confidence score (0–1) with an evidence_type indicator.

**Behavioral description:**  
The `Finding` object includes:
1. A `confidence` field (float, 0.0 to 1.0) indicating how confident the system is in the finding.
2. An evidence type indicator (via `evidence_payload.source` or a dedicated `evidence_type` field) distinguishing:
   - **Heuristic-only findings**: Pattern-matched by rules without screenshot/AI confirmation (lower confidence, typically ≤0.75)
   - **AI-evidence-backed findings**: Confirmed by Nova classification with screenshot evidence (higher confidence, typically >0.75)

The confidence score is computed based on the classification method used and the strength of evidence.

**Pass condition:** Every finding has a `confidence` value where `0.0 ≤ confidence ≤ 1.0`. The evidence type is derivable from `evidence_payload.source` (e.g., `"mock_classifier"`, `"nova_classifier"`, `"heuristic"`) or an explicit `evidence_type` field. Heuristic-only findings have systematically lower confidence than AI-backed findings for equivalent patterns.  
**Fail condition:** Confidence values are outside the 0–1 range, all findings have identical confidence scores, or there is no way to distinguish heuristic vs. AI-backed findings.

**Evidence requirements:**
- API response showing ≥3 findings with varying confidence values
- At least one heuristic-only finding (`source` ≠ nova) with confidence ≤ 0.75
- At least one AI-backed finding (if Nova is available) with confidence > 0.75
- Backend code showing confidence computation logic

*Note: The `confidence` field already exists on the Finding model (`backend/app/models/audit.py:66`). The evidence source is already tracked in `evidence_payload.source`. This assertion validates the scoring range and semantic distinction are meaningful.*

---

### VAL-ADV-004 · Confidence Scoring — UI Display

**Title:** The report page displays confidence scores per finding.

**Behavioral description:**  
Each `FindingCard` component renders the confidence score as a percentage (e.g., "85% confidence") in a signal pill or badge. The display format is `{Math.round(confidence * 100)}% confidence`. Optionally, findings with low confidence (e.g., <50%) are visually flagged with a different color or warning icon.

**Pass condition:** Every FindingCard displays a confidence percentage that matches `Math.round(finding.confidence * 100)`. The display is a visible pill/badge element. The value updates correctly for different findings (not hardcoded).  
**Fail condition:** Confidence is not displayed, the percentage does not match the underlying data, or all findings show the same confidence value.

**Evidence requirements:**
- Screenshot of ≥2 FindingCards showing different confidence percentages
- DOM inspection confirming the displayed percentage matches the API data
- Cross-reference with API response `confidence` field values

*Note: This behavior already exists in `FindingCard.tsx:82`. This assertion confirms it functions correctly and remains intact.*

---

### VAL-ADV-005 · False-Positive Suppression — Data Marking

**Title:** Known false-positive patterns are suppressed or flagged in findings data.

**Behavioral description:**  
The system identifies and handles known false-positive patterns (e.g., legitimate cookie banners that follow best practices, standard pricing displays). Suppressed findings are either:
- **Filtered out** entirely from the findings response (with a count of suppressed items returned in metadata), OR
- **Marked** with a `suppressed` or `false_positive` flag on the finding object, allowing the UI to filter or de-emphasize them.

The suppression logic is based on configurable rules or patterns maintained in the backend.

**Pass condition:** At least one of the following is true:
1. The findings response includes metadata (e.g., `suppressed_count`) indicating how many findings were suppressed, OR
2. Individual findings include a boolean `suppressed` / `false_positive` field, and at least one finding in test data is marked as suppressed.

**Fail condition:** There is no suppression mechanism — all pattern matches are treated equally with no false-positive handling. No field, metadata, or filtering logic exists.

**Evidence requirements:**
- API response showing suppression metadata or `suppressed` field on findings
- Backend code showing the suppression rule definitions and application logic
- Example of a pattern that triggers suppression (e.g., a cookie banner with equal-weight accept/reject buttons)

---

### VAL-ADV-006 · False-Positive Suppression — UI Display

**Title:** Suppressed findings are visually distinguished or filtered in the UI.

**Behavioral description:**  
When suppressed/false-positive findings are present in the data:
- If findings are marked (not filtered server-side), the UI renders them with a visual distinction: muted styling, strikethrough, "Likely false positive" badge, or collapsed by default.
- Optionally, a toggle allows users to show/hide suppressed findings.
- The finding count in the executive summary reflects the non-suppressed count, with a note about suppressed items (e.g., "12 findings (3 suppressed)").

**Pass condition:** Suppressed findings are visually distinct from confirmed findings (different opacity, badge, or section). The executive summary finding count is accurate and notes suppressions if any exist.  
**Fail condition:** Suppressed and confirmed findings look identical, or suppressed findings inflate the finding count without disclosure.

**Evidence requirements:**
- Screenshot showing a suppressed finding with distinct visual treatment
- Screenshot of the executive summary showing the suppressed count annotation
- (If toggle exists) Screenshots showing the list with suppressed findings hidden and shown

---

### VAL-ADV-007 · Regulatory Mapping — Contextual Relevance

**Title:** Regulatory categories are contextually relevant to the finding's pattern family and scenario.

**Behavioral description:**  
The regulatory mapping is not random — it follows logical associations:
- `cookie_consent` scenario findings → likely tagged `GDPR`, `DSA`, `CPRA`
- `checkout_flow` hidden costs findings → likely tagged `FTC`
- `confirmshaming` pattern findings → likely tagged `FTC`, `DSA`
- `sneaking` / `hidden_costs` patterns → likely tagged `FTC`, `CPRA`
- Privacy-related patterns → likely tagged `GDPR`, `CPRA`

**Pass condition:** For ≥80% of findings with regulatory categories, the assigned regulations are contextually appropriate for the finding's `pattern_family` and `scenario`. Cookie consent + GDPR is valid; cookie consent + FTC-only is less expected but not invalid.  
**Fail condition:** Regulatory categories appear randomly assigned with no correlation to the finding's pattern or scenario (e.g., checkout hidden costs tagged only with GDPR and no FTC).

**Evidence requirements:**
- Table of ≥5 findings showing `pattern_family`, `scenario`, and `regulatory_categories`
- Assessment of contextual relevance for each mapping
- Backend code showing the mapping logic (rules, prompt, or lookup table)

---

### VAL-ADV-008 · Confidence Scoring — Evidence Source Label

**Title:** FindingCard displays a human-readable evidence source label indicating the classification method.

**Behavioral description:**  
Each FindingCard shows a label derived from `evidence_payload.source_label` (or equivalent) indicating whether the finding was generated by:
- Mock classifier (e.g., "Mock evidence")
- Heuristic rules (e.g., "Rule-based")
- Nova AI classifier (e.g., "Nova AI evidence")
- Hybrid approach (e.g., "Browser + mock AI")

This label helps users understand the provenance and reliability of each finding.

**Pass condition:** Every FindingCard displays a source label pill/badge. The label text varies based on the actual classification method used. The label is human-readable (not raw class names like "MockClassifierProvider").  
**Fail condition:** No source label is shown, or all findings show the same generic label regardless of their actual source.

**Evidence requirements:**
- Screenshot of FindingCards showing different source labels
- API response showing the `evidence_payload.source_label` values
- Mapping from backend provider names to human-readable labels

*Note: The `sourceLabel` display already exists in `FindingCard.tsx:80` via `evidence_payload.source_label`. This assertion validates it renders correctly with meaningful labels.*

---

## Summary Matrix

| ID | Area | Title | New Feature? |
|---|---|---|---|
| VAL-UI-001 | UI Demo | History — List Display | ✅ New |
| VAL-UI-002 | UI Demo | History — Filter/Search | ✅ New |
| VAL-UI-003 | UI Demo | History — Click to View | ✅ New |
| VAL-UI-004 | UI Demo | History — Rerun Audit | ✅ New |
| VAL-UI-005 | UI Demo | History — Compare Audits | ✅ New |
| VAL-UI-006 | UI Demo | Persona Diff View | ✅ New |
| VAL-UI-007 | UI Demo | Screenshot Timeline | ✅ New |
| VAL-UI-008 | UI Demo | Findings Grouped by Scenario | 🔄 Existing |
| VAL-UI-009 | UI Demo | PDF Export | ✅ New |
| VAL-UI-010 | UI Demo | Navigation — All Pages | ✅ New |
| VAL-UI-011 | UI Demo | Error States | 🔄 Partial |
| VAL-UI-012 | UI Demo | Loading States | 🔄 Partial |
| VAL-UI-013 | UI Demo | Visual Polish | ✅ New |
| VAL-UI-014 | UI Demo | RunPage Live Progress | 🔄 Existing |
| VAL-ADV-001 | Adv Intelligence | Regulatory Mapping — Data | ✅ New |
| VAL-ADV-002 | Adv Intelligence | Regulatory Mapping — UI | ✅ New |
| VAL-ADV-003 | Adv Intelligence | Confidence Scoring — Data | 🔄 Existing |
| VAL-ADV-004 | Adv Intelligence | Confidence Scoring — UI | 🔄 Existing |
| VAL-ADV-005 | Adv Intelligence | False-Positive Suppression — Data | ✅ New |
| VAL-ADV-006 | Adv Intelligence | False-Positive Suppression — UI | ✅ New |
| VAL-ADV-007 | Adv Intelligence | Regulatory Mapping — Relevance | ✅ New |
| VAL-ADV-008 | Adv Intelligence | Evidence Source Label | 🔄 Existing |
