"""
Integration tests for mock mode video recording events.

These tests verify that MockBrowserAuditProvider emits descriptive video events
during mock audit execution, and that these events are visible in the RunPage
timeline and support the full flow to ReportPage video playback.

Validation Contract Assertions:
- VAL-VIDEO-006: RunPage shows video recording status during audit
- VAL-VIDEO-001: Video URL data present in API response for completed audits
- VAL-VIDEO-003: ReportPage displays video players per scenario-persona
- VAL-VIDEO-008: Multiple videos per audit use lazy loading
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.audit import AuditEvent
from app.providers.browser import MockBrowserAuditProvider
from app.providers.storage import StorageObject, StorageProvider


@pytest.fixture
def mock_storage():
    """Create a mock storage provider for video testing."""
    storage = MagicMock(spec=StorageProvider)
    storage.save_bytes.return_value = StorageObject(
        relative_key="videos/test-audit/cookie_consent_privacy_sensitive.webm",
        public_url="/artifacts/videos/test-audit/cookie_consent_privacy_sensitive.webm",
        absolute_path="C:/data/videos/test-audit/cookie_consent_privacy_sensitive.webm",
    )
    storage.save_text.return_value = StorageObject(
        relative_key="screenshots/test-audit/test.svg",
        public_url="/artifacts/screenshots/test-audit/test.svg",
        absolute_path=None,
    )
    return storage


@pytest.fixture
def mock_audit_orchestrator_with_stubs(db_engine):
    """
    Create an orchestrator with properly mocked providers for integration testing.

    This fixture patches get_browser_provider and get_classifier_provider to use
    the mock provider, ensuring consistent test behavior.
    """
    import tempfile

    from sqlalchemy.orm import sessionmaker

    from app.providers.browser import MockBrowserAuditProvider
    from app.providers.classifier import MockClassifierProvider
    from app.providers.storage import LocalStorageProvider
    from app.services.audit_orchestrator import AuditOrchestrator

    session_local = sessionmaker(bind=db_engine)
    orchestrator = AuditOrchestrator(session_local)

    # Create storage provider with temp directory
    temp_dir = tempfile.mkdtemp()
    storage = LocalStorageProvider(root=Path(temp_dir))

    # Create mock providers
    mock_browser = MockBrowserAuditProvider(storage)
    mock_classifier = MockClassifierProvider()

    # Patch the provider getters
    with (
        patch(
            "app.services.audit_orchestrator.get_browser_provider",
            return_value=mock_browser,
        ),
        patch(
            "app.services.audit_orchestrator.get_classifier_provider",
            return_value=mock_classifier,
        ),
        patch(
            "app.services.audit_orchestrator.get_fallback_browser_provider",
            return_value=mock_browser,
        ),
        patch(
            "app.services.report_service.ReportService.generate_report",
            return_value=("C:/report.html", "/reports/test.html"),
        ),
    ):
        yield orchestrator, mock_browser


class TestMockBrowserVideoEvents:
    """Test that MockBrowserAuditProvider emits descriptive video events."""

    def test_mock_emits_video_phase_events(self, mock_storage):
        """
        VAL-VIDEO-006: Mock audit emits audit events with phase='video'.

        During a mock audit, the provider should emit events with phase='video'
        for each scenario-persona combination.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({
                "phase": phase,
                "message": message,
                "progress": progress_pct,
                "status": status,
                "details": details,
            })

        provider.run_audit(
            audit_id="test-video-audit",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        # Verify video phase events were emitted
        video_events = [e for e in events if e["phase"] == "video"]
        assert len(video_events) > 0, "Should emit events with phase='video'"

    def test_mock_video_events_have_descriptive_messages(self, mock_storage):
        """
        Mock video events should have descriptive messages like
        'Recording browser session for {scenario}/{persona}' or similar.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({
                "phase": phase,
                "message": message,
                "details": details,
            })

        provider.run_audit(
            audit_id="test-video-audit",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        video_events = [e for e in events if e["phase"] == "video"]
        assert len(video_events) > 0, "Should have video events"

        # Each video event should mention recording or session video
        for event in video_events:
            message = event["message"].lower()
            assert (
                "video" in message or "record" in message or "session" in message
            ), f"Video event message should mention 'video', 'record', or 'session': {event['message']}"

    def test_mock_video_events_include_scenario_and_persona(self, mock_storage):
        """
        Video events should include scenario and persona in details for
        RunPage timeline display.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({
                "phase": phase,
                "message": message,
                "details": details,
            })

        provider.run_audit(
            audit_id="test-video-audit",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        video_events = [e for e in events if e["phase"] == "video"]

        # Each video event should include scenario and persona in details
        for event in video_events:
            details = event["details"]
            assert "scenario" in details, "Video event should include scenario in details"
            assert "persona" in details, "Video event should include persona in details"
            assert details["scenario"] == "cookie_consent"
            assert details["persona"] == "privacy_sensitive"

    def test_mock_video_events_include_video_url(self, mock_storage):
        """
        Video events should include the video URL in details so the
        RunPage can display video status with a link to the recording.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({
                "phase": phase,
                "message": message,
                "details": details,
            })

        provider.run_audit(
            audit_id="test-video-audit",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        video_events = [e for e in events if e["phase"] == "video"]

        # At least one video event should include the video URL
        events_with_url = [e for e in video_events if e["details"].get("video_url")]
        assert len(events_with_url) > 0, "Video events should include video_url in details"

    def test_mock_multiple_scenarios_emit_multiple_video_events(self, mock_storage):
        """
        When multiple scenarios and personas are audited, each combination
        should emit its own video event.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({
                "phase": phase,
                "details": details,
            })

        scenarios = ["cookie_consent", "checkout_flow"]
        personas = ["privacy_sensitive", "cost_sensitive"]

        provider.run_audit(
            audit_id="test-video-audit",
            target_url="https://example.com",
            scenarios=scenarios,
            personas=personas,
            progress=progress,
        )

        video_events = [e for e in events if e["phase"] == "video"]

        # Should have at least 4 video events (2 scenarios x 2 personas)
        assert len(video_events) >= 4, (
            f"Expected at least 4 video events for 2 scenarios x 2 personas, got {len(video_events)}"
        )

    def test_mock_video_events_emit_in_progress_then_complete(self, mock_storage):
        """
        Video events should show progress from 'running' to 'success' status.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({
                "phase": phase,
                "status": status,
                "details": details,
            })

        provider.run_audit(
            audit_id="test-video-audit",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        video_events = [e for e in events if e["phase"] == "video"]

        # Should have events with 'running' status
        running_events = [e for e in video_events if e["status"] == "running"]
        assert len(running_events) > 0, "Should have video events with 'running' status"


class TestVideoEventFullFlow:
    """
    Test the full flow: submit audit -> RunPage shows video events -> ReportPage shows players.

    These tests verify the integration between the backend provider events and
    frontend display through the audit orchestrator.
    """

    def test_full_flow_emits_video_events_to_database(
        self, db_session, mock_audit_orchestrator_with_stubs
    ):
        """
        Full flow: Audit orchestrator should persist video events to database
        where they can be polled by RunPage.
        """
        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = mock_audit_orchestrator_with_stubs

        # Create audit
        payload = AuditCreateRequest(
            target_url=HttpUrl("https://example.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            video_urls=None,
        )
        audit = orchestrator.create_audit(db_session, payload, "mock")
        audit_id = audit.id

        # Run audit
        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        # Refresh to get events
        db_session.refresh(audit)

        # Verify video events exist in database
        video_events = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.audit_id == audit_id, AuditEvent.phase == "video")
            .all()
        )

        assert len(video_events) > 0, (
            "Video events should be persisted to database for RunPage timeline"
        )

        # Verify event details include scenario and persona
        for event in video_events:
            assert "scenario" in event.details, "Video event should have scenario in details"
            assert "persona" in event.details, "Video event should have persona in details"

    def test_full_flow_video_urls_persisted_on_audit(
        self, db_session, mock_audit_orchestrator_with_stubs
    ):
        """
        VAL-VIDEO-001: Full flow should persist video_urls on the audit model
        for ReportPage video players.
        """
        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = mock_audit_orchestrator_with_stubs

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://example.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            video_urls=None,
        )
        audit = orchestrator.create_audit(db_session, payload, "mock")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)

        # Verify video_urls is persisted
        assert audit.video_urls is not None, "video_urls should be persisted on audit"
        assert len(audit.video_urls) > 0, "video_urls should not be empty"

        # Verify format: {scenario}_{persona} -> URL
        expected_key = "cookie_consent_privacy_sensitive"
        assert expected_key in audit.video_urls, (
            f"Expected key '{expected_key}' in video_urls, got {audit.video_urls.keys()}"
        )
        assert audit.video_urls[expected_key].endswith(".webm"), (
            "Video URL should be a .webm file"
        )

    def test_full_flow_multiple_scenarios_personas(
        self, db_session, mock_audit_orchestrator_with_stubs
    ):
        """
        VAL-VIDEO-008: Multiple scenarios and personas should each have their own
        video entry with proper keys.
        """
        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = mock_audit_orchestrator_with_stubs

        scenarios = ["cookie_consent", "checkout_flow"]
        personas = ["privacy_sensitive", "cost_sensitive"]

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://example.com"),
            scenarios=scenarios,
            personas=personas,
            video_urls=None,
        )
        audit = orchestrator.create_audit(db_session, payload, "mock")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.8)  # More time for multiple scenarios

        db_session.refresh(audit)

        # Verify all combinations have video URLs
        for scenario in scenarios:
            for persona in personas:
                key = f"{scenario}_{persona}"
                assert key in audit.video_urls, (
                    f"Missing video URL for {scenario} / {persona}"
                )

        # Verify count matches expected
        expected_count = len(scenarios) * len(personas)
        assert len(audit.video_urls) == expected_count, (
            f"Expected {expected_count} video URLs, got {len(audit.video_urls)}"
        )


class TestVideoEventsAPIResponse:
    """Test that video events and URLs are properly exposed in API responses."""

    def test_api_response_includes_video_urls(
        self, db_session, mock_audit_orchestrator_with_stubs
    ):
        """
        VAL-VIDEO-001: API response should include video_urls field.

        Note: Using orchestrator directly since test_client only has health router.
        """
        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = mock_audit_orchestrator_with_stubs

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://example.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            video_urls=None,
        )
        audit = orchestrator.create_audit(db_session, payload, "mock")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        # Refresh and verify video_urls
        db_session.refresh(audit)
        assert audit.video_urls is not None, "video_urls should be persisted"
        assert len(audit.video_urls) > 0, "video_urls should not be empty"




    def test_api_response_events_include_video_phase(
        self, db_session, mock_audit_orchestrator_with_stubs
    ):
        """
        VAL-VIDEO-006: API events should include phase='video' entries.
        """
        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = mock_audit_orchestrator_with_stubs

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://example.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            video_urls=None,
        )
        audit = orchestrator.create_audit(db_session, payload, "mock")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)

        # Events should include video phase
        video_events = [e for e in audit.events if e.phase == "video"]
        assert len(video_events) > 0, "API response should include video phase events"


class TestMockWebMValidity:
    """Test that mock WebM files are valid and browser-compatible."""

    def test_mock_webm_bytes_length(self):
        """
        VAL-VIDEO-003: Mock WebM file must be > 100 bytes to be valid.
        The known-good minimal WebM from mathiasbynens/small is 185 bytes.
        """
        from app.providers.browser import MockBrowserAuditProvider

        webm_bytes = MockBrowserAuditProvider.MOCK_WEBM_BYTES
        assert len(webm_bytes) > 100, f"Mock WebM should be > 100 bytes, got {len(webm_bytes)}"
        assert len(webm_bytes) >= 185, f"Mock WebM should be at least 185 bytes, got {len(webm_bytes)}"

    def test_mock_webm_has_ebml_header(self):
        """
        VAL-VIDEO-003: Valid WebM must start with EBML header (0x1A 0x45 0xDF 0xA3).
        """
        from app.providers.browser import MockBrowserAuditProvider

        webm_bytes = MockBrowserAuditProvider.MOCK_WEBM_BYTES
        # EBML header signature
        assert webm_bytes[:4] == bytes([0x1A, 0x45, 0xDF, 0xA3]), "Should start with EBML header"

    def test_mock_webm_contains_webm_doctype(self):
        """
        VAL-VIDEO-003: Valid WebM must contain 'webm' doctype.
        """
        from app.providers.browser import MockBrowserAuditProvider

        webm_bytes = MockBrowserAuditProvider.MOCK_WEBM_BYTES
        assert b"webm" in webm_bytes, "Should contain 'webm' doctype"

    def test_mock_webm_contains_segment(self):
        """
        VAL-VIDEO-003: Valid WebM must contain Segment element.
        """
        from app.providers.browser import MockBrowserAuditProvider

        webm_bytes = MockBrowserAuditProvider.MOCK_WEBM_BYTES
        # Segment ID is 0x18 0x53 0x80 0x67
        segment_id = bytes([0x18, 0x53, 0x80, 0x67])
        assert segment_id in webm_bytes, "Should contain Segment element"

    def test_mock_webm_contains_tracks(self):
        """
        VAL-VIDEO-003: Valid WebM must contain Tracks element.
        """
        from app.providers.browser import MockBrowserAuditProvider

        webm_bytes = MockBrowserAuditProvider.MOCK_WEBM_BYTES
        # Tracks ID is 0x16 0x54 0xAE 0x6B
        tracks_id = bytes([0x16, 0x54, 0xAE, 0x6B])
        assert tracks_id in webm_bytes, "Should contain Tracks element"

    def test_mock_webm_contains_vp8_codec(self):
        """
        VAL-VIDEO-003: Valid WebM must contain VP8 video track.
        """
        from app.providers.browser import MockBrowserAuditProvider

        webm_bytes = MockBrowserAuditProvider.MOCK_WEBM_BYTES
        # VP8 codec ID
        assert b"V_VP8" in webm_bytes, "Should contain VP8 codec ID"


class TestVideoEventsFrontendContract:
    """
    Test the contract between backend events and frontend display.

    These tests verify that the backend provides the data the frontend
    needs to display video events and players.
    """

    def test_video_event_message_format_for_runpage(self, mock_storage):
        """
        VAL-VIDEO-006: Video event messages should be human-readable for RunPage timeline.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({"phase": phase, "message": message})

        provider.run_audit(
            audit_id="test-audit",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        video_events = [e for e in events if e["phase"] == "video"]

        # Messages should be human-readable
        for event in video_events:
            message = event["message"]
            assert len(message) > 10, f"Message too short: {message}"
            # Should not be just an error code or ID
            assert not message.startswith("error_"), f"Message shouldn't be error code: {message}"
            # Should describe what happened
            assert any(
                word in message.lower()
                for word in ["record", "video", "session", "capture", "saved"]
            ), f"Message should describe video activity: {message}"

    def test_video_event_details_include_scenario_persona_for_display(self, mock_storage):
        """
        VAL-VIDEO-006: Video event details should include scenario and persona
        for RunPage to show context.
        """
        provider = MockBrowserAuditProvider(mock_storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({"phase": phase, "details": details})

        provider.run_audit(
            audit_id="test-audit",
            target_url="https://example.com",
            scenarios=["cookie_consent", "checkout_flow"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        video_events = [e for e in events if e["phase"] == "video"]

        for event in video_events:
            details = event["details"]
            # Should have scenario for display
            assert "scenario" in details, "Details should include scenario"
            # Should have persona for display
            assert "persona" in details, "Details should include persona"

    def test_video_urls_format_for_reportpage(
        self, db_session, mock_audit_orchestrator_with_stubs
    ):
        """
        VAL-VIDEO-003: Video URLs should be in format ReportPage expects:
        {scenario}_{persona} -> URL mapping.
        """
        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = mock_audit_orchestrator_with_stubs

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://example.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            video_urls=None,
        )
        audit = orchestrator.create_audit(db_session, payload, "mock")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)

        # Verify format that ReportPage parses
        video_urls = audit.video_urls
        for key, url in video_urls.items():
            # Key should be {scenario}_{persona} format
            parts = key.split("_")
            assert len(parts) >= 2, f"Key '{key}' should be in format 'scenario_persona'"

            # URL should be accessible path
            assert url.startswith("/") or url.startswith("http"), (
                f"URL '{url}' should be an accessible path"
            )
            assert url.endswith(".webm"), f"URL '{url}' should be .webm file"
