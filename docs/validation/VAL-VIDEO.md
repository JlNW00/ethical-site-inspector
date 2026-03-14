# Validation Contract: Video Replay Feature

**Feature area:** Video Replay (browser session recordings)
**Date:** 2026-03-14
**Status:** Draft

---

## Overview

The Video Replay feature enables Nova Act's `record_video=True` to capture `.webm` browser session recordings during audits. Videos are uploaded to S3 via the existing `StorageProvider`, stored as URLs on audit models (new DB columns/fields), and rendered in an HTML5 video player on `ReportPage`. Each video is associated per-scenario-per-persona. In mock mode, mock video URLs (or placeholder data) must be produced to keep the feature testable without a real browser.

---

### VAL-VIDEO-001: Video URL present in API response for completed audits

**Behavioral description:**
When a completed audit is fetched via `GET /api/audits/{audit_id}`, each scenario+persona combination in the response must include a `video_url` field. For mock-mode audits, the value must be a non-empty string pointing to a valid local artifact path (e.g., `/artifacts/videos/{audit_id}/{scenario}_{persona}.webm`) or a mock placeholder URL. For live/hybrid-mode audits, it must be a valid S3 public URL or local path. The field may be `null` only if video recording was explicitly disabled or if the audit predates the video feature (backwards compatibility).

**Pass condition:** `GET /api/audits/{id}` returns JSON where every scenario-persona entry surfaces a `video_url` string (or the audit-level response includes a `video_urls` mapping keyed by `{scenario}_{persona}`). No entry for a completed audit that ran with video enabled has `video_url: null`.

**Fail condition:** Any completed audit response omits the `video_url` field entirely, or returns `null` for a scenario-persona pair that was executed with video recording enabled.

**Evidence:** Network response body from `GET /api/audits/{audit_id}` (JSON), network response body from `GET /api/audits/{audit_id}/findings` (JSON).

---

### VAL-VIDEO-002: Video URL resolves with correct content-type

**Behavioral description:**
Every `video_url` surfaced in the API response must resolve via HTTP GET to a valid response. For S3-hosted videos, the response `Content-Type` header must be `video/webm`. For local artifacts served by FastAPI's static file mount, the `Content-Type` must be `video/webm`. The response status must be `200 OK`. The response body must be non-empty (file size > 0 bytes).

**Pass condition:** `HEAD` or `GET` request to each `video_url` returns HTTP 200 with `Content-Type: video/webm` and `Content-Length > 0`.

**Fail condition:** Any `video_url` returns a non-200 status code, incorrect `Content-Type`, or zero-length body.

**Evidence:** `curl -I {video_url}` output showing status, content-type, and content-length headers. Console network tab screenshot.

---

### VAL-VIDEO-003: Mock mode produces mock video data

**Behavioral description:**
When the backend runs in mock mode (the default, `MockBrowserAuditProvider`), the audit orchestrator must produce video artifacts alongside the existing mock SVG screenshots. These may be minimal valid `.webm` files, placeholder videos, or synthetic short clips. The `MockBrowserAuditProvider._build_observation()` method must populate `video_url` on the `ObservationEvidence` (or equivalent new field) and the `StorageProvider.save_bytes()` call must succeed with `content_type="video/webm"`.

**Pass condition:** After a mock audit completes, the audit response includes `video_url` values for each scenario-persona pair, and those URLs resolve to a non-empty response (even if the video content is a placeholder/stub).

**Fail condition:** Mock audits produce `null` or missing `video_url` fields, or the URL returns 404.

**Evidence:** API response JSON from mock audit, `curl -I` of each mock video URL, storage directory listing (`data/` folder contents).

---

### VAL-VIDEO-004: ReportPage displays a video player per scenario-persona

**Behavioral description:**
On the ReportPage (`/audits/{auditId}/report`), for each scenario-persona combination that has a video URL, an HTML5 `<video>` element must be rendered. The video player must appear in a recognizable location—either within each finding card's evidence section, or in a dedicated "Video Replay" section analogous to the existing "Screenshot Timeline" section. Each video player must be labeled with its associated scenario and persona names (e.g., "Cookie Consent — Privacy Sensitive").

**Pass condition:** For a completed audit with N scenario-persona combinations each having a `video_url`, exactly N `<video>` elements (or equivalent video player components) are present in the DOM. Each is labeled with the correct scenario and persona.

**Fail condition:** No `<video>` elements are rendered, or the count does not match the number of video URLs, or labels are missing/incorrect.

**Evidence:** DOM inspection (browser DevTools Elements panel), screenshot of the ReportPage showing video players with labels.

---

### VAL-VIDEO-005: Video player supports play, pause, and seek

**Behavioral description:**
Each video player on ReportPage must support standard HTML5 video controls: play, pause, and seek (scrubbing the progress bar). The `<video>` element must have the `controls` attribute set (i.e., `<video controls>`). When the user clicks play, the video must begin playback (the `currentTime` advances, the play button toggles to pause). When paused, the video freezes at the current frame.

**Pass condition:** Clicking the play button starts video playback (verified by `currentTime > 0` after a short delay). Clicking pause stops playback. Dragging the seek bar changes `currentTime` to the sought position.

**Fail condition:** Play/pause does not toggle, video does not advance, or seek bar is non-functional.

**Evidence:** Browser automation assertions (e.g., Playwright: `video.evaluate('v => v.paused')` before and after click), screenshot showing play/pause state.

---

### VAL-VIDEO-006: Video player supports fullscreen

**Behavioral description:**
Each video player must support entering and exiting fullscreen mode via the browser's native fullscreen control (part of the HTML5 `controls` attribute). When the user activates fullscreen, the video element expands to fill the viewport. Pressing Escape or clicking the fullscreen toggle exits fullscreen.

**Pass condition:** After activating fullscreen, `document.fullscreenElement` references the `<video>` element (or its container). After exiting, `document.fullscreenElement` is `null`.

**Fail condition:** Fullscreen button is absent, does not enter fullscreen, or cannot be exited.

**Evidence:** Console assertion of `document.fullscreenElement`, screenshot in fullscreen mode.

---

### VAL-VIDEO-007: Video loading state shown while video buffers

**Behavioral description:**
While a video is loading (network fetch in progress, buffering), the user must see a visible loading indicator. This can be the browser's native video loading spinner (the default for `<video controls>`) or a custom overlay spinner/skeleton. The video player must not display a broken/empty rectangle with no feedback.

**Pass condition:** Before the video `canplay` event fires, a loading indicator is visible (native browser spinner or custom component). After `canplay`, the first frame or poster is visible.

**Fail condition:** The video area appears as an empty black/white rectangle with no loading feedback while the video loads.

**Evidence:** Screenshot captured before video `canplay` event, DOM inspection for loading indicators.

---

### VAL-VIDEO-008: Video error state when URL fails to load

**Behavioral description:**
If a `video_url` is unreachable (404, network error, CORS block), the video player must display a clear error state rather than a silent failure. This should include a user-friendly message (e.g., "Video unavailable" or "Failed to load video") and optionally a retry action. The browser console must not show an unhandled error. The `<video>` element's `error` event must be caught and handled.

**Pass condition:** When a video URL returns 404, the video player area shows an error message visible to the user. No unhandled exceptions in the browser console.

**Fail condition:** The video area is blank/broken with no user-facing error message, or the console shows uncaught errors.

**Evidence:** Screenshot of error state, browser console output (filtered for errors), network tab showing the failed request.

---

### VAL-VIDEO-009: No video player rendered when video_url is null or absent

**Behavioral description:**
For audits that predate the video feature (backwards compatibility) or for scenario-persona combinations where video was not captured, the `video_url` will be `null` or absent from the API response. In this case, the ReportPage must NOT render a broken `<video>` element. The page should either omit the video section entirely or display a graceful fallback message (e.g., "No video recording available for this scenario").

**Pass condition:** When `video_url` is `null`/absent for all scenario-persona pairs, no `<video>` element is in the DOM. When only some pairs have videos, only those pairs show video players.

**Fail condition:** A `<video>` element with `src=""` or `src="null"` is rendered, causing a broken player or console error.

**Evidence:** DOM inspection showing no `<video>` elements (or correct count), console errors check, screenshot.

---

### VAL-VIDEO-010: Video replay section visible in Screenshot Timeline area

**Behavioral description:**
On the ReportPage, the video replay section must appear in a logical location relative to the existing "Screenshot Timeline" section. The recommended placement is either (a) a new "Video Replay" section immediately after the Screenshot Timeline, or (b) inline within the Screenshot Timeline with video entries interspersed among screenshot entries. The section must have a heading (e.g., "Session Recordings" or "Video Replay") and a subtitle describing the content.

**Pass condition:** A section with a heading containing "video", "recording", or "replay" (case-insensitive) is visible on the ReportPage. It appears in a logical position relative to the Screenshot Timeline and Findings sections.

**Fail condition:** No video section heading is present, or video players are placed in an unexpected/confusing location (e.g., inside the Executive Summary).

**Evidence:** Screenshot of full ReportPage layout, DOM inspection for section heading text.

---

### VAL-VIDEO-011: RunPage shows video recording status during audit

**Behavioral description:**
On the RunPage (`/audits/{auditId}/run`), when an audit is running with video recording enabled, the activity timeline or run-state metrics should indicate that video is being recorded. This can be an event in the timeline (e.g., "Recording video for cookie_consent / privacy_sensitive") or a metric card showing "Video recording: active". This gives users confidence that the feature is working.

**Pass condition:** At least one timeline event or metric indicator references video recording during an active audit with video enabled. The indicator updates as scenarios progress.

**Fail condition:** No indication of video recording activity appears on the RunPage during audit execution.

**Evidence:** Screenshot of RunPage during a running audit, timeline event list inspection.

---

### VAL-VIDEO-012: PersonaDiffPage includes video comparison capability

**Behavioral description:**
On the PersonaDiffPage (`/audits/{auditId}/diff`), which shows side-by-side persona comparisons, video players should be available for each persona column if video URLs exist. This allows users to compare the actual browsing sessions between personas visually. Each persona column should embed a video player (or a link to watch the video) within the persona's evidence section.

**Pass condition:** On PersonaDiffPage, each persona column that has associated video URLs displays a video player or a "Watch session" link. Videos can be played independently per persona.

**Fail condition:** PersonaDiffPage shows no video content even though video URLs exist in the audit data.

**Evidence:** Screenshot of PersonaDiffPage with video players visible in persona columns, DOM inspection.

---

### VAL-VIDEO-013: FindingCard shows video evidence when available

**Behavioral description:**
The `FindingCard` component currently shows screenshot thumbnails from `evidence_payload.screenshot_urls`. When `evidence_payload.video_url` (or equivalent field) is present for a finding, the FindingCard should display a video player or a clickable video thumbnail in the evidence section, alongside existing screenshots. The video provides richer evidence context for the specific finding.

**Pass condition:** When a finding has a `video_url` in its `evidence_payload`, a video element or video link is rendered in the FindingCard's evidence area. It does not replace screenshots but complements them.

**Fail condition:** FindingCard ignores `video_url` entirely even when present, or shows a broken video element.

**Evidence:** Screenshot of FindingCard with video evidence, DOM inspection of the component.

---

### VAL-VIDEO-014: Database migration adds video columns without data loss

**Behavioral description:**
The Alembic migration that adds video-related columns to the database (e.g., `video_urls` JSON column on the `audits` table, or `video_url` on `findings` table) must be additive and non-destructive. Existing audit records must retain all their data after the migration. New columns must default to `null` or empty values for existing rows. The migration must be reversible (downgrade path works).

**Pass condition:** After running `alembic upgrade head`, all existing audits are queryable with correct data. New `video_url` columns exist with `null` defaults. `alembic downgrade -1` removes the new columns without data loss.

**Fail condition:** Migration fails, existing data is corrupted, or downgrade path does not work.

**Evidence:** `alembic upgrade head` output, SQL query showing existing audit data intact with new nullable columns, `alembic downgrade -1` output.

---

### VAL-VIDEO-015: StorageProvider handles .webm upload with correct content-type

**Behavioral description:**
Both `LocalStorageProvider` and `S3StorageProvider` must correctly handle `.webm` video file uploads. When `save_bytes()` is called with `content_type="video/webm"`, the file must be stored and retrievable with the correct MIME type. For S3, the `ContentType` metadata must be set on the object. For local storage, the static file server must serve the file with the correct `Content-Type` header.

**Pass condition:** After `save_bytes(key, payload, "video/webm")`, the returned `public_url` serves the file with `Content-Type: video/webm`. For S3, the object metadata shows `ContentType: video/webm`.

**Fail condition:** The file is stored but served with an incorrect content-type (e.g., `application/octet-stream`), causing the browser `<video>` element to fail to play it.

**Evidence:** `curl -I` response headers from the stored video URL, S3 object metadata (for S3 provider).

---
