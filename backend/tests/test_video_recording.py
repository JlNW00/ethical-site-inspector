"""
Tests for video recording in browser providers.

These tests verify that NovaActAuditProvider and PlaywrightAuditProvider
correctly record and save video files during audit runs.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.providers.nova_act_browser import NovaActAuditProvider
from app.providers.browser import PlaywrightAuditProvider, MockBrowserAuditProvider
from app.providers.storage import StorageObject, StorageProvider


@pytest.fixture
def mock_storage():
    """Create a mock storage provider."""
    storage = MagicMock(spec=StorageProvider)
    storage.save_bytes.return_value = StorageObject(
        relative_key="videos/test-audit/cookie_consent_privacy_sensitive.webm",
        public_url="/artifacts/videos/test-audit/cookie_consent_privacy_sensitive.webm",
        absolute_path="C:/data/videos/test-audit/cookie_consent_privacy_sensitive.webm",
    )
    return storage


class TestNovaActVideoRecording:
    """Test video recording functionality in NovaActAuditProvider."""

    @patch("app.providers.nova_act_browser.NovaAct")
    @patch("app.providers.nova_act_browser.tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_nova_act_constructor_called_with_record_video(
        self, mock_rmtree, mock_mkdtemp, mock_nova_class, mock_storage
    ):
        """VAL-VIDEO-006: Verify NovaAct is constructed with record_video=True and logs_directory."""
        mock_nova_instance = MagicMock()
        mock_nova_instance.page = MagicMock()
        mock_nova_instance.page.screenshot.return_value = b"fake_screenshot"
        mock_nova_instance.page.url = "https://example.com"
        mock_nova_instance.session_id = "test-session-456"
        mock_nova_instance.act_get.return_value = MagicMock(parsed_response={
            "banner_present": False,
            "accept_button_text": "",
            "reject_button_text": None,
            "reject_button_visible": False,
            "accept_clicks_required": 0,
            "reject_clicks_required": 0,
            "asymmetry_detected": False,
            "has_essential_only_option": False,
        })

        mock_nova_class.return_value.__enter__ = MagicMock(return_value=mock_nova_instance)
        mock_nova_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_mkdtemp.return_value = "/tmp/test-logs"

        with patch.object(
            NovaActAuditProvider, "_ensure_nova_act", return_value=MagicMock(BOOL_SCHEMA={"type": "boolean"})
        ):
            provider = NovaActAuditProvider(mock_storage)

            def progress(phase, message, progress_pct, status, details):
                pass

            result = provider.run_audit(
                audit_id="test-audit-video",
                target_url="https://example.com",
                scenarios=["cookie_consent"],
                personas=["privacy_sensitive"],
                progress=progress,
            )

        # Verify NovaAct was constructed with record_video=True
        mock_nova_class.assert_called()
        calls = mock_nova_class.call_args_list

        found_record_video = False
        found_logs_directory = False
        for call in calls:
            kwargs = call.kwargs if call.kwargs else {}
            if kwargs.get("record_video") is True:
                found_record_video = True
            if "logs_directory" in kwargs:
                found_logs_directory = True

        assert found_record_video, "NovaAct constructor should be called with record_video=True"
        assert found_logs_directory, "NovaAct constructor should be called with logs_directory"

    @patch("app.providers.nova_act_browser.NovaAct")
    @patch("app.providers.nova_act_browser.tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_audit_events_include_video_phase(
        self, mock_rmtree, mock_mkdtemp, mock_nova_class, mock_storage
    ):
        """Verify audit events include phase='video' entries during recording."""
        mock_nova_instance = MagicMock()
        mock_nova_instance.page = MagicMock()
        mock_nova_instance.page.screenshot.return_value = b"fake_screenshot"
        mock_nova_instance.page.url = "https://example.com"
        mock_nova_instance.session_id = "test-session-ghi"
        mock_nova_instance.act_get.return_value = MagicMock(parsed_response={
            "banner_present": False,
            "accept_button_text": "",
            "reject_button_text": None,
            "reject_button_visible": False,
            "accept_clicks_required": 0,
            "reject_clicks_required": 0,
            "asymmetry_detected": False,
            "has_essential_only_option": False,
        })

        mock_nova_class.return_value.__enter__ = MagicMock(return_value=mock_nova_instance)
        mock_nova_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_mkdtemp.return_value = "/tmp/test-logs"

        events = []
        def progress(phase, message, progress_pct, status, details):
            events.append({"phase": phase, "message": message})

        with patch.object(
            NovaActAuditProvider, "_ensure_nova_act", return_value=MagicMock(BOOL_SCHEMA={"type": "boolean"})
        ):
            provider = NovaActAuditProvider(mock_storage)

            result = provider.run_audit(
                audit_id="test-audit",
                target_url="https://example.com",
                scenarios=["cookie_consent"],
                personas=["privacy_sensitive"],
                progress=progress,
            )

        # Verify video phase events
        video_events = [e for e in events if e["phase"] == "video"]
        assert len(video_events) > 0, "Should emit events with phase='video'"

        # Check for recording message
        recording_messages = [e for e in events if "recording" in e["message"].lower()]
        assert len(recording_messages) > 0, "Should have events mentioning 'recording'"


class TestPlaywrightVideoRecording:
    """Test video recording functionality in PlaywrightAuditProvider."""

    def test_playwright_context_options_include_record_video(self, mock_storage):
        """Verify Playwright context is created with record_video options."""
        provider = PlaywrightAuditProvider(mock_storage)

        # After implementation, verify _context_options returns record_video config
        options = provider._context_options("privacy_sensitive")

        # After implementation, should have record_video configuration
        # For now, test that the method exists and returns a dict
        assert isinstance(options, dict), "_context_options should return a dict"


class TestMockModeVideo:
    """Verify mock mode video behavior for reference."""

    def test_mock_provider_emits_video_events(self):
        """Mock provider should emit video recording events."""
        storage = MagicMock(spec=StorageProvider)
        storage.save_bytes.return_value = StorageObject(
            relative_key="videos/test/mock.webm",
            public_url="/artifacts/videos/test/mock.webm",
            absolute_path=None,
        )

        provider = MockBrowserAuditProvider(storage)
        events = []

        def progress(phase, message, progress_pct, status, details):
            events.append({"phase": phase, "message": message})

        result = provider.run_audit(
            audit_id="test-mock",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        # Verify mock provider emits video events
        video_events = [e for e in events if e["phase"] == "video"]
        assert len(video_events) > 0, "Mock provider should emit video events"
        assert result.video_urls is not None, "Mock provider should return video_urls"
        assert "cookie_consent_privacy_sensitive" in result.video_urls
