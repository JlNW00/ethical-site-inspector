"""Tests for provider registry provider selection logic."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.providers.browser import MockBrowserAuditProvider, PlaywrightAuditProvider
from app.providers.nova_act_browser import NovaActAuditProvider
from app.services.provider_registry import get_browser_provider


class TestProviderRegistryBrowserProvider:
    """Test provider registry returns correct provider per mode."""

    @patch("app.services.provider_registry.NOVA_ACT_AVAILABLE", True)
    def test_live_mode_returns_nova_act_provider(self):
        """Live mode should return NovaActAuditProvider when NOVA_ACT_AVAILABLE."""
        with patch("app.services.provider_registry.get_settings") as mock_get_settings:
            with patch("app.services.provider_registry.get_storage_provider") as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage

                mock_settings = MagicMock()
                mock_settings.effective_mode = "live"
                mock_settings.local_storage_root = Path("/tmp/test")
                mock_get_settings.return_value = mock_settings

                provider = get_browser_provider("live")
                assert isinstance(provider, NovaActAuditProvider)

    @patch("app.services.provider_registry.NOVA_ACT_AVAILABLE", False)
    def test_live_mode_fallback_to_mock_when_nova_unavailable(self):
        """Live mode should fallback to MockBrowserAuditProvider when NOVA_ACT_AVAILABLE is False."""
        with patch("app.services.provider_registry.get_settings") as mock_get_settings:
            with patch("app.services.provider_registry.get_storage_provider") as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage

                mock_settings = MagicMock()
                mock_settings.effective_mode = "live"
                mock_settings.local_storage_root = Path("/tmp/test")
                mock_get_settings.return_value = mock_settings

                provider = get_browser_provider("live")
                assert isinstance(provider, MockBrowserAuditProvider)

    def test_mock_mode_returns_mock_browser_provider(self):
        """Mock mode should return MockBrowserAuditProvider."""
        with patch("app.services.provider_registry.get_settings") as mock_get_settings:
            with patch("app.services.provider_registry.get_storage_provider") as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage

                mock_settings = MagicMock()
                mock_settings.effective_mode = "mock"
                mock_settings.local_storage_root = Path("/tmp/test")
                mock_get_settings.return_value = mock_settings

                provider = get_browser_provider("mock")
                assert isinstance(provider, MockBrowserAuditProvider)

    def test_hybrid_mode_returns_playwright_provider(self):
        """Hybrid mode should return PlaywrightAuditProvider."""
        with patch("app.services.provider_registry.get_settings") as mock_get_settings:
            with patch("app.services.provider_registry.get_storage_provider") as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage

                mock_settings = MagicMock()
                mock_settings.effective_mode = "hybrid"
                mock_settings.local_storage_root = Path("/tmp/test")
                mock_get_settings.return_value = mock_settings

                provider = get_browser_provider("hybrid")
                assert isinstance(provider, PlaywrightAuditProvider)

    @patch("app.services.provider_registry.NOVA_ACT_AVAILABLE", True)
    def test_live_mode_provider_class_name_contains_nova(self):
        """Live mode provider class name should contain 'NovaAct'."""
        with patch("app.services.provider_registry.get_settings") as mock_get_settings:
            with patch("app.services.provider_registry.get_storage_provider") as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage

                mock_settings = MagicMock()
                mock_settings.effective_mode = "live"
                mock_settings.local_storage_root = Path("/tmp/test")
                mock_get_settings.return_value = mock_settings

                provider = get_browser_provider("live")
                assert "NovaAct" in provider.__class__.__name__

    def test_hybrid_mode_unchanged(self):
        """Hybrid mode should NOT use NovaActAuditProvider (uses Playwright)."""
        with patch("app.services.provider_registry.get_settings") as mock_get_settings:
            with patch("app.services.provider_registry.get_storage_provider") as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage

                mock_settings = MagicMock()
                mock_settings.effective_mode = "hybrid"
                mock_settings.local_storage_root = Path("/tmp/test")
                mock_get_settings.return_value = mock_settings

                provider = get_browser_provider("hybrid")
                assert not isinstance(provider, NovaActAuditProvider)
                assert isinstance(provider, PlaywrightAuditProvider)

    def test_mock_mode_unchanged(self):
        """Mock mode should NOT use NovaActAuditProvider or PlaywrightAuditProvider."""
        with patch("app.services.provider_registry.get_settings") as mock_get_settings:
            with patch("app.services.provider_registry.get_storage_provider") as mock_get_storage:
                mock_storage = MagicMock()
                mock_get_storage.return_value = mock_storage

                mock_settings = MagicMock()
                mock_settings.effective_mode = "mock"
                mock_settings.local_storage_root = Path("/tmp/test")
                mock_get_settings.return_value = mock_settings

                provider = get_browser_provider("mock")
                assert not isinstance(provider, NovaActAuditProvider)
                assert not isinstance(provider, PlaywrightAuditProvider)
                assert isinstance(provider, MockBrowserAuditProvider)
