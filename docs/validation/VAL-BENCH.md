# Benchmark Mode — Validation Contract Assertions

> Feature: Benchmark Mode allows users to submit 2–5 URLs for comparative auditing, spawning individual audits per URL and presenting side-by-side trust-score comparisons on a dedicated BenchmarkPage.

---

### VAL-BENCH-001: Benchmark Mode Toggle on SubmitPage

When the user is on SubmitPage, a "Benchmark Mode" toggle/switch is visible below or alongside the existing Target URL field. Clicking it transitions the form from single-URL mode to multi-URL mode: the single `target_url` input is replaced (or augmented) by a dynamic list of URL input fields with add/remove controls, and the submit button label updates to indicate benchmark submission (e.g., "Start benchmark audit").

**Pass condition:** Toggling ON shows ≥2 URL input fields with an "Add URL" control; toggling OFF reverts to the original single-URL input. The toggle state is visually distinct (e.g., highlighted pill or switch).
**Evidence:** Screenshot of SubmitPage in both toggle states; DOM snapshot confirming the presence/absence of multi-URL fields and the `data-testid="benchmark-toggle"` element.

---

### VAL-BENCH-002: Multi-URL Input Validation — Minimum of 2 URLs

When benchmark mode is active and the user attempts to submit with fewer than 2 non-empty, valid URLs, the form must display an inline validation error and prevent submission.

**Pass condition:** Submitting with 0 or 1 URL shows an error message (e.g., "Benchmark mode requires at least 2 URLs") and no API call is made (`POST /api/benchmarks` is never fired). The submit button remains enabled but the form does not proceed.
**Evidence:** Screenshot showing the error state; network tab confirming no outgoing POST request; assertion on the error text content.

---

### VAL-BENCH-003: Multi-URL Input Validation — Maximum of 5 URLs

When benchmark mode is active and the user has 5 URL fields populated, the "Add URL" control must be disabled or hidden. Attempting to programmatically add a 6th URL must be rejected by the API with a 422 response.

**Pass condition:** The "Add URL" button is disabled/hidden once 5 fields exist. A forced `POST /api/benchmarks` with 6 URLs returns HTTP 422 with a descriptive validation error.
**Evidence:** Screenshot showing disabled "Add URL" at 5 URLs; API response body from a 6-URL request; frontend DOM state.

---

### VAL-BENCH-004: Multi-URL Input Validation — URL Format

Each URL field in benchmark mode must validate that the entered value is a well-formed HTTP/HTTPS URL before submission. Invalid entries (e.g., `not-a-url`, `ftp://example.com`, empty string) should trigger per-field inline validation errors.

**Pass condition:** Entering an invalid URL in any benchmark field displays a field-level error indicator. The form does not submit until all URL fields contain valid `http://` or `https://` URLs. The backend `POST /api/benchmarks` rejects payloads with malformed URLs (HTTP 422).
**Evidence:** Screenshot of per-field validation errors; API 422 response for malformed URL payload.

---

### VAL-BENCH-005: Benchmark Creation API — Happy Path

A `POST /api/benchmarks` request with 2–5 valid URLs, selected scenarios, and selected personas returns HTTP 201 with a `Benchmark` object containing: `id` (UUID), `status: "queued"`, `urls` (list matching input), `audit_ids` (list of spawned audit IDs, one per URL), `created_at` timestamp.

**Pass condition:** Response status is 201. The response body includes all required fields. `len(audit_ids) == len(urls)`. Each `audit_id` corresponds to a valid Audit record retrievable via `GET /api/audits/{id}` with `status` in `["queued", "running"]`.
**Evidence:** Full API response JSON; follow-up `GET /api/audits/{id}` for each spawned audit confirming existence and correct `target_url`.

---

### VAL-BENCH-006: Post-Submit Navigation — Redirect to BenchmarkPage

After successful benchmark creation from SubmitPage, the user is automatically navigated to `/benchmarks/{benchmarkId}` (the BenchmarkPage) rather than the single-audit RunPage.

**Pass condition:** `window.location.pathname` matches `/benchmarks/{uuid}` after submission. The BenchmarkPage loads and displays the benchmark's constituent URLs and their initial "queued" status.
**Evidence:** Browser URL assertion; BenchmarkPage DOM showing the correct benchmark ID and URL list.

---

### VAL-BENCH-007: BenchmarkPage — Aggregate Progress Tracking

While constituent audits are running, BenchmarkPage displays per-URL progress indicators (e.g., progress bars or percentage values) and an overall benchmark progress computed as the average of individual audit progress values. The page polls for updates (similar to RunPage's 1.5-second polling pattern).

**Pass condition:** Each URL row shows its own progress percentage. The aggregate progress meter reflects the mean of individual values. When all audits reach "completed" or "failed", polling stops and the comparison view is shown.
**Evidence:** DOM snapshots at multiple polling intervals showing increasing progress values; network tab showing periodic `GET` requests for audit status.

---

### VAL-BENCH-008: BenchmarkPage — Side-by-Side Trust Score Comparison

Once all constituent audits have completed, BenchmarkPage renders a comparison view with: (a) a ranked list of URLs by trust score (highest first), (b) trust score values and visual meters for each URL, (c) a delta indicator between the highest and lowest scores.

**Pass condition:** All completed audit URLs appear in descending trust-score order. Each entry shows the numeric trust score and a `<ProgressMeter>` component. The score delta between best and worst is displayed.
**Evidence:** Screenshot of the comparison view; DOM assertions on ordering, score values, and delta text.

---

### VAL-BENCH-009: BenchmarkPage — Scenario Breakdown Grid

BenchmarkPage includes a scenario breakdown section that shows, for each selected scenario, the finding counts across all benchmarked URLs in a grid/table format, enabling cross-site comparison at the scenario level.

**Pass condition:** A grid with rows = scenarios and columns = URLs is rendered. Each cell shows the finding count for that scenario/URL pair. Scenarios with zero findings show "0" (not blank).
**Evidence:** Screenshot of scenario grid; DOM content assertions for cell values matching the sum of findings per scenario per audit.

---

### VAL-BENCH-010: BenchmarkPage — Unified Summary

BenchmarkPage shows a textual summary section that synthesizes the benchmark results, including: which URL scored highest/lowest, common dark pattern families observed across sites, and an overall risk assessment.

**Pass condition:** The summary section is non-empty when all audits are completed. It references the highest-scoring and lowest-scoring URLs by name. It lists at least one dark pattern family if findings exist.
**Evidence:** Text content of the summary section; assertion that URL references match actual benchmark URLs.

---

### VAL-BENCH-011: Navigation — BenchmarkPage to Individual Audit Reports

Each URL entry on BenchmarkPage includes a clickable link or button that navigates the user to the individual audit's ReportPage (`/audits/{auditId}/report`). A "Back to Benchmark" link on ReportPage (or browser back) returns the user to the BenchmarkPage.

**Pass condition:** Clicking a URL's "View Report" link navigates to `/audits/{auditId}/report` where the correct audit data loads. The ReportPage (or breadcrumb) provides a route back to `/benchmarks/{benchmarkId}`.
**Evidence:** Navigation flow screenshots; URL bar assertions at each step; DOM presence of back-link on ReportPage.

---

### VAL-BENCH-012: HistoryPage — Benchmarks Listed Alongside Audits

HistoryPage displays benchmark entries in the audit list, visually distinguished from regular single-URL audits (e.g., a "Benchmark" badge or icon, showing the count of URLs). Clicking a benchmark row navigates to BenchmarkPage, not ReportPage.

**Pass condition:** After creating a benchmark, HistoryPage shows at least one row with a benchmark indicator. The row displays the URL count (e.g., "3 URLs"). Clicking it navigates to `/benchmarks/{id}`, not `/audits/{id}/report`.
**Evidence:** HistoryPage screenshot showing benchmark row with badge; click navigation URL assertion.

---

### VAL-BENCH-013: Error Handling — Partial Audit Failure in Benchmark

If one or more (but not all) constituent audits fail while others complete, BenchmarkPage still renders the comparison for completed audits, marks failed URLs with an error badge, and does not block the overall benchmark from reaching a "completed" (partial) state.

**Pass condition:** BenchmarkPage shows completed audits in the comparison view with trust scores. Failed audits display an error badge and "N/A" or "--" for trust score. The benchmark `status` transitions to `"completed"` (or `"partial"`) rather than `"failed"`. The unified summary acknowledges the failure.
**Evidence:** API response for benchmark showing mixed audit statuses; BenchmarkPage screenshot with error badges on failed URLs; summary text mentioning the failure.

---

### VAL-BENCH-014: API — Get Benchmark and List Benchmarks

`GET /api/benchmarks/{id}` returns the full Benchmark object including `id`, `status`, `urls`, `audit_ids`, `created_at`, `updated_at`, and an aggregated `trust_scores` map. `GET /api/benchmarks` returns a list of all benchmarks sorted by `created_at` descending.

**Pass condition:** `GET /api/benchmarks/{id}` returns HTTP 200 with all expected fields. `GET /api/benchmarks/{nonexistent-id}` returns HTTP 404. `GET /api/benchmarks` returns a JSON array sorted by `created_at` DESC. After creating 2 benchmarks, the list endpoint returns both.
**Evidence:** Full API response JSON for each endpoint; 404 response for invalid ID; list ordering verification.

---

### VAL-BENCH-015: Benchmark Mode State Isolation

Toggling benchmark mode on SubmitPage does not corrupt or lose the user's existing scenario and persona selections. Switching between benchmark mode and single-audit mode preserves these selections. Submitting in single-audit mode after toggling off benchmark mode creates a normal audit (not a benchmark).

**Pass condition:** Select 3 scenarios and 2 personas, toggle benchmark ON, then OFF — selections remain intact. Submit in single-audit mode → a normal `POST /api/audits` call is made (not `/api/benchmarks`), and navigation goes to `/audits/{id}/run`.
**Evidence:** DOM assertions on checkbox states before and after toggle; network request URL and payload inspection; navigation URL after single-audit submit.
