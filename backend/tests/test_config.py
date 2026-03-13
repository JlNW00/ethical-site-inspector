"""Tests for app.core.config – Settings class behaviour."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core.config import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> Settings:
    """Construct a Settings instance with explicit overrides (env-var aliases).

    We pass empty strings for optional AWS/S3 fields so that pydantic-settings
    does NOT fall through to .env file values on this machine.
    """
    defaults = {
        "AUDIT_MODE": "auto",
        "USE_REAL_BROWSER": "false",
        "DATABASE_URL": "sqlite:///:memory:",
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
        "S3_BUCKET_NAME": "",
        "S3_ENDPOINT_URL": "",
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# Settings defaults
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    def test_app_name_default(self):
        s = _make_settings()
        assert s.app_name == "EthicalSiteInspector API"

    def test_api_prefix_default(self):
        s = _make_settings()
        assert s.api_prefix == "/api"

    def test_configured_mode_default(self):
        s = _make_settings()
        assert s.configured_mode == "auto"


# ---------------------------------------------------------------------------
# effective_mode logic
# ---------------------------------------------------------------------------


class TestEffectiveMode:
    def test_auto_no_browser_no_nova_returns_mock(self):
        s = _make_settings(AUDIT_MODE="auto", USE_REAL_BROWSER="false")
        assert s.effective_mode == "mock"

    def test_auto_with_browser_no_nova_returns_hybrid(self):
        s = _make_settings(AUDIT_MODE="auto", USE_REAL_BROWSER="true")
        assert s.effective_mode == "hybrid"

    def test_auto_with_browser_and_nova_returns_live(self):
        s = _make_settings(
            AUDIT_MODE="auto",
            USE_REAL_BROWSER="true",
            AWS_ACCESS_KEY_ID="AKID",
            AWS_SECRET_ACCESS_KEY="secret",
        )
        assert s.effective_mode == "live"

    def test_explicit_mock_always_returns_mock(self):
        s = _make_settings(
            AUDIT_MODE="mock",
            USE_REAL_BROWSER="true",
            AWS_ACCESS_KEY_ID="AKID",
            AWS_SECRET_ACCESS_KEY="secret",
        )
        assert s.effective_mode == "mock"

    def test_hybrid_with_browser_returns_hybrid(self):
        s = _make_settings(AUDIT_MODE="hybrid", USE_REAL_BROWSER="true")
        assert s.effective_mode == "hybrid"

    def test_hybrid_without_browser_falls_back_to_mock(self):
        s = _make_settings(AUDIT_MODE="hybrid", USE_REAL_BROWSER="false")
        assert s.effective_mode == "mock"

    def test_live_with_all_ready_returns_live(self):
        s = _make_settings(
            AUDIT_MODE="live",
            USE_REAL_BROWSER="true",
            AWS_ACCESS_KEY_ID="AKID",
            AWS_SECRET_ACCESS_KEY="secret",
        )
        assert s.effective_mode == "live"

    def test_live_with_browser_no_nova_returns_hybrid(self):
        s = _make_settings(AUDIT_MODE="live", USE_REAL_BROWSER="true")
        assert s.effective_mode == "hybrid"

    def test_live_without_browser_returns_mock(self):
        s = _make_settings(AUDIT_MODE="live", USE_REAL_BROWSER="false")
        assert s.effective_mode == "mock"


# ---------------------------------------------------------------------------
# nova_ready property
# ---------------------------------------------------------------------------


class TestNovaReady:
    def test_nova_ready_true_when_both_keys_present(self):
        s = _make_settings(AWS_ACCESS_KEY_ID="AKID", AWS_SECRET_ACCESS_KEY="secret")
        assert s.nova_ready is True

    def test_nova_ready_false_when_key_missing(self):
        s = _make_settings(AWS_ACCESS_KEY_ID="AKID")
        assert s.nova_ready is False

    def test_nova_ready_false_when_secret_missing(self):
        s = _make_settings(AWS_SECRET_ACCESS_KEY="secret")
        assert s.nova_ready is False

    def test_nova_ready_false_when_both_missing(self):
        s = _make_settings()
        assert s.nova_ready is False


# ---------------------------------------------------------------------------
# s3_ready property
# ---------------------------------------------------------------------------


class TestS3Ready:
    def test_s3_ready_true_when_bucket_and_endpoint_set(self):
        s = _make_settings(S3_BUCKET_NAME="bucket", S3_ENDPOINT_URL="https://s3.example.com")
        assert s.s3_ready is True

    def test_s3_ready_false_when_bucket_missing(self):
        s = _make_settings(S3_ENDPOINT_URL="https://s3.example.com")
        assert s.s3_ready is False

    def test_s3_ready_false_when_endpoint_missing(self):
        s = _make_settings(S3_BUCKET_NAME="bucket")
        assert s.s3_ready is False

    def test_s3_ready_false_when_both_missing(self):
        s = _make_settings()
        assert s.s3_ready is False
