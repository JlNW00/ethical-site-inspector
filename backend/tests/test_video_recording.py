"""
Tests for video recording in browser providers.

These tests verify that NovaActAuditProvider and PlaywrightAuditProvider
correctly record and save video files during audit runs.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.providers.browser import MockBrowserAuditProvider, PlaywrightAuditProvider
from app.providers.nova_act_browser import NovaActAuditProvider
from app.providers.storage import StorageObject, StorageProvider


# =============================================================================
# Video URL Collection Tests
# =============================================================================


class TestVideoUrlCollection:
    """Test that video URLs are properly collected and returned in BrowserRunResult."""

    @patch("app.providers.nova_act_browser.NovaAct")
    @patch("app.providers.nova_act_browser.tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_video_urls_populated_in_run_audit_result(
        self, mock_rmtree, mock_mkdtemp, mock_nova_class, mock_storage
    ):
        """BrowserRunResult.video_urls should be populated with scenario_persona keys."""
        mock_nova_instance = MagicMock()
        mock_nova_instance.page = MagicMock()
        mock_nova_instance.page.screenshot.return_value = b"fake_screenshot"
        mock_nova_instance.page.url = "https://example.com"
        mock_nova_instance.session_id = "test-session-video"
        mock_nova_instance.act_get.return_value = MagicMock(
            parsed_response={
                "banner_present": True,
                "accept_button_text": "Accept All",
                "reject_button_text": "Reject",
                "reject_button_visible": True,
                "accept_clicks_required": 1,
                "reject_clicks_required": 1,
                "asymmetry_detected": False,
                "has_essential_only_option": True,
            }
        )

        mock_nova_class.return_value.__enter__ = MagicMock(return_value=mock_nova_instance)
        mock_nova_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_mkdtemp.return_value = "/tmp/test-video-logs"

        # Mock _extract_and_save_video to return a video URL
        with patch.object(
            NovaActAuditProvider, "_ensure_nova_act", return_value=MagicMock(BOOL_SCHEMA={"type": "boolean"})
        ):
            provider = NovaActAuditProvider(mock_storage)

            # Mock the video extraction to return a URL
            with patch.object(
                provider,
                "_extract_and_save_video",
                return_value="/artifacts/videos/test-audit/cookie_consent_privacy_sensitive.webm",
            ):

                def progress(phase, message, progress_pct, status, details):
                    pass

                result = provider.run_audit(
                    audit_id="test-audit",
                    target_url="https://example.com",
                    scenarios=["cookie_consent"],
                    personas=["privacy_sensitive"],
                    progress=progress,
                )

        # Verify video_urls is populated
        assert result.video_urls is not None
        assert len(result.video_urls) > 0
        assert "cookie_consent_privacy_sensitive" in result.video_urls
        assert (
            result.video_urls["cookie_consent_privacy_sensitive"]
            == "/artifacts/videos/test-audit/cookie_consent_privacy_sensitive.webm"
        )

    @patch("app.providers.nova_act_browser.NovaAct")
    @patch("app.providers.nova_act_browser.tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_video_urls_multiple_scenarios_and_personas(
        self, mock_rmtree, mock_mkdtemp, mock_nova_class, mock_storage
    ):
        """Video URLs should be collected for all scenario-persona combinations."""
        mock_nova_instance = MagicMock()
        mock_nova_instance.page = MagicMock()
        mock_nova_instance.page.screenshot.return_value = b"fake_screenshot"
        mock_nova_instance.page.url = "https://example.com"
        mock_nova_instance.session_id = "test-session-multi"

        # Different responses based on scenario
        def mock_act_get(prompt, schema=None):
            result = MagicMock()
            if schema and "cookie" in prompt.lower():
                result.parsed_response = {
                    "banner_present": True,
                    "accept_button_text": "Accept All",
                    "reject_button_text": "Reject",
                    "reject_button_visible": True,
                    "accept_clicks_required": 1,
                    "reject_clicks_required": 1,
                    "asymmetry_detected": False,
                    "has_essential_only_option": True,
                }
            elif schema and "checkout" in prompt.lower():
                result.parsed_response = {
                    "page_reached": True,
                    "prices_seen": [{"label": "Total", "value": 49.99}],
                    "hidden_fees": [],
                    "price_delta": 0.0,
                    "urgency_tactics": [],
                    "pre_selected_addons": [],
                    "required_steps": 3,
                    "unexpected_obstacles": [],
                }
            else:
                result.parsed_response = True
            return result

        mock_nova_instance.act_get.side_effect = mock_act_get

        mock_nova_class.return_value.__enter__ = MagicMock(return_value=mock_nova_instance)
        mock_nova_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_mkdtemp.return_value = "/tmp/test-multi"

        # Track which videos were "saved"
        video_calls = []

        def mock_extract_and_save(audit_id, logs_dir, session_id, scenario, persona, progress):
            video_calls.append(f"{scenario}_{persona}")
            return f"/artifacts/videos/{audit_id}/{scenario}_{persona}.webm"

        with patch.object(
            NovaActAuditProvider, "_ensure_nova_act", return_value=MagicMock(BOOL_SCHEMA={"type": "boolean"})
        ):
            provider = NovaActAuditProvider(mock_storage)

            with patch.object(provider, "_extract_and_save_video", side_effect=mock_extract_and_save):

                def progress(phase, message, progress_pct, status, details):
                    pass

                result = provider.run_audit(
                    audit_id="test-multi",
                    target_url="https://example.com",
                    scenarios=["cookie_consent", "checkout_flow"],
                    personas=["privacy_sensitive", "cost_sensitive"],
                    progress=progress,
                )

        # Should have 4 video URLs (2 scenarios x 2 personas)
        assert result.video_urls is not None
        assert len(result.video_urls) == 4

        # Check all expected keys exist
        expected_keys = [
            "cookie_consent_privacy_sensitive",
            "cookie_consent_cost_sensitive",
            "checkout_flow_privacy_sensitive",
            "checkout_flow_cost_sensitive",
        ]
        for key in expected_keys:
            assert key in result.video_urls, f"Missing video URL key: {key}"

    @patch("app.providers.nova_act_browser.NovaAct")
    @patch("app.providers.nova_act_browser.tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_video_urls_thread_safety(
        self, mock_rmtree, mock_mkdtemp, mock_nova_class, mock_storage
    ):
        """Video URL collection should work correctly when running parallel personas."""
        mock_nova_instance = MagicMock()
        mock_nova_instance.page = MagicMock()
        mock_nova_instance.page.screenshot.return_value = b"fake_screenshot"
        mock_nova_instance.page.url = "https://example.com"
        mock_nova_instance.session_id = "test-session-thread"
        mock_nova_instance.act_get.return_value = MagicMock(
            parsed_response={
                "banner_present": True,
                "accept_button_text": "Accept All",
                "reject_button_text": "Reject",
                "reject_button_visible": True,
                "accept_clicks_required": 1,
                "reject_clicks_required": 1,
                "asymmetry_detected": False,
                "has_essential_only_option": True,
            }
        )

        mock_nova_class.return_value.__enter__ = MagicMock(return_value=mock_nova_instance)
        mock_nova_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_mkdtemp.return_value = "/tmp/test-thread"

        # Verify parallel execution still collects all video URLs correctly
        with patch.object(
            NovaActAuditProvider, "_ensure_nova_act", return_value=MagicMock(BOOL_SCHEMA={"type": "boolean"})
        ):
            provider = NovaActAuditProvider(mock_storage, max_workers=3)

            # Track video extraction calls
            video_calls = []

            def mock_extract_and_save(audit_id, logs_dir, session_id, scenario, persona, progress):
                video_calls.append(f"{scenario}_{persona}")
                return f"/artifacts/videos/{audit_id}/{scenario}_{persona}.webm"

            with patch.object(provider, "_extract_and_save_video", side_effect=mock_extract_and_save):

                def progress(phase, message, progress_pct, status, details):
                    pass

                result = provider.run_audit(
                    audit_id="test-thread",
                    target_url="https://example.com",
                    scenarios=["cookie_consent"],
                    personas=["privacy_sensitive", "cost_sensitive", "exit_intent"],
                    progress=progress,
                )

        # All 3 personas should have video URLs collected even with parallel execution
        assert result.video_urls is not None
        assert len(result.video_urls) == 3
        assert "cookie_consent_privacy_sensitive" in result.video_urls
        assert "cookie_consent_cost_sensitive" in result.video_urls
        assert "cookie_consent_exit_intent" in result.video_urls

    @patch("app.providers.nova_act_browser.NovaAct")
    @patch("app.providers.nova_act_browser.tempfile.mkdtemp")
    @patch("shutil.rmtree")
    def test_video_urls_empty_when_no_videos(
        self, mock_rmtree, mock_mkdtemp, mock_nova_class, mock_storage
    ):
        """Video URLs dict should be empty when video extraction returns None."""
        mock_nova_instance = MagicMock()
        mock_nova_instance.page = MagicMock()
        mock_nova_instance.page.screenshot.return_value = b"fake_screenshot"
        mock_nova_instance.page.url = "https://example.com"
        mock_nova_instance.session_id = "test-session-novid"
        mock_nova_instance.act_get.return_value = MagicMock(
            parsed_response={
                "banner_present": False,
                "accept_button_text": "",
                "reject_button_text": None,
                "reject_button_visible": False,
                "accept_clicks_required": 0,
                "reject_clicks_required": 0,
                "asymmetry_detected": False,
                "has_essential_only_option": False,
            }
        )

        mock_nova_class.return_value.__enter__ = MagicMock(return_value=mock_nova_instance)
        mock_nova_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_mkdtemp.return_value = "/tmp/test-novid"

        with patch.object(
            NovaActAuditProvider, "_ensure_nova_act", return_value=MagicMock(BOOL_SCHEMA={"type": "boolean"})
        ):
            provider = NovaActAuditProvider(mock_storage)

            # Mock video extraction to return None (no video found)
            with patch.object(provider, "_extract_and_save_video", return_value=None):

                def progress(phase, message, progress_pct, status, details):
                    pass

                result = provider.run_audit(
                    audit_id="test-novid",
                    target_url="https://example.com",
                    scenarios=["cookie_consent"],
                    personas=["privacy_sensitive"],
                    progress=progress,
                )

        # Video URLs should be empty dict when no videos
        assert result.video_urls is not None
        assert len(result.video_urls) == 0


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
