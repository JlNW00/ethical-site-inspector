# Video Data Model

Conventions and data formats for the video recording feature.

**What belongs here:** Key formats, data flow, parsing conventions.

---

## video_urls Key Format

The `video_urls` dict on the Audit model uses keys in the format `{scenario}_{persona}`, where both scenario and persona are snake_case identifiers from the taxonomy (e.g., `cookie_consent_privacy_sensitive`).

**Important:** Since both scenario and persona names contain underscores internally (e.g., `cookie_consent`, `privacy_sensitive`), the underscore separator between scenario and persona is ambiguous. You **cannot** reliably parse the key by splitting on `_`.

**Correct parsing approach:** Cross-reference the key against `audit.selected_scenarios` and `audit.selected_personas` to find the valid split point. For each key, try matching `{scenario}_{persona}` for all known scenarios and personas until one matches.

**Backend source:** `backend/app/providers/browser.py` generates keys via `f"{scenario}_{persona}"`.

## Video File Format

- Content-Type: `video/webm`
- Storage key pattern: `videos/{audit_id}/{scenario}_{persona}.webm`
- Mock mode: 37-byte EBML header placeholder (not playable, but correct MIME type)
- Real mode: Full WebM video from Nova Act or Playwright recording

## Data Flow

1. Browser provider runs scenario for persona
2. Video file extracted from temp directory (Nova Act: `{logs_directory}/{session_id}/session_video_tab-0.webm`)
3. Saved via `StorageProvider.save_bytes()` with `content_type='video/webm'`
4. URL collected in `BrowserRunResult.video_urls` dict
5. `AuditOrchestrator._run_audit_internal()` persists `video_urls` on the Audit model
6. Frontend fetches via `GET /api/audits/{id}` and renders `<video>` elements
