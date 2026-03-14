"""Tests for Pydantic schemas in app.schemas.audit."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.schemas.audit import (
    AuditCreateRequest,
    FindingRead,
    HealthResponse,
    ReadinessResponse,
)

# ---------------------------------------------------------------------------
# AuditCreateRequest
# ---------------------------------------------------------------------------


class TestAuditCreateRequest:
    def test_valid_url(self):
        req = AuditCreateRequest(target_url="https://example.com")
        assert str(req.target_url) == "https://example.com/"

    def test_valid_url_with_path(self):
        req = AuditCreateRequest(target_url="https://shop.example.com/checkout")
        assert "shop.example.com" in str(req.target_url)

    def test_invalid_url_raises(self):
        with pytest.raises(ValidationError):
            AuditCreateRequest(target_url="not-a-url")

    def test_missing_url_raises(self):
        with pytest.raises(ValidationError):
            AuditCreateRequest()  # type: ignore[call-arg]

    def test_default_scenarios(self):
        req = AuditCreateRequest(target_url="https://example.com")
        assert req.scenarios == ["cookie_consent", "checkout_flow"]

    def test_default_personas(self):
        req = AuditCreateRequest(target_url="https://example.com")
        assert req.personas == ["privacy_sensitive", "cost_sensitive"]

    def test_custom_scenarios(self):
        req = AuditCreateRequest(
            target_url="https://example.com",
            scenarios=["subscription_cancellation"],
        )
        assert req.scenarios == ["subscription_cancellation"]


# ---------------------------------------------------------------------------
# HealthResponse
# ---------------------------------------------------------------------------


class TestHealthResponse:
    def test_health_response_creation(self):
        now = datetime.now(UTC)
        resp = HealthResponse(status="ok", timestamp=now)
        assert resp.status == "ok"
        assert resp.timestamp == now
        assert resp.version == "0.1.0"


# ---------------------------------------------------------------------------
# ReadinessResponse
# ---------------------------------------------------------------------------


class TestReadinessResponse:
    def test_readiness_response_creation(self):
        resp = ReadinessResponse(
            status="ready",
            configured_mode="auto",
            effective_mode="mock",
            browser_provider="MockBrowserAuditProvider",
            classifier_provider="MockClassifierProvider",
            storage_provider="LocalStorageProvider",
            nova_ready=False,
            playwright_ready=False,
            storage_ready=True,
            seeded_demo_audit_id=None,
        )
        assert resp.status == "ready"
        assert resp.effective_mode == "mock"
        assert resp.nova_ready is False
        assert resp.seeded_demo_audit_id is None

    def test_readiness_response_with_demo_audit(self):
        resp = ReadinessResponse(
            status="ready",
            configured_mode="live",
            effective_mode="live",
            browser_provider="PlaywrightAuditProvider",
            classifier_provider="LiveNovaClassifierProvider",
            storage_provider="S3StorageProvider",
            nova_ready=True,
            playwright_ready=True,
            storage_ready=True,
            seeded_demo_audit_id="abc-123",
        )
        assert resp.seeded_demo_audit_id == "abc-123"
        assert resp.nova_ready is True


# ---------------------------------------------------------------------------
# FindingRead (from_attributes)
# ---------------------------------------------------------------------------


class TestFindingRead:
    def test_finding_read_from_dict(self):
        now = datetime.now(UTC)
        data = {
            "id": "f-001",
            "scenario": "cookie_consent",
            "persona": "privacy_sensitive",
            "pattern_family": "asymmetric_choice",
            "severity": "high",
            "title": "Accept without reject",
            "explanation": "The consent banner lacks explicit reject.",
            "remediation": "Add a reject button.",
            "evidence_excerpt": "Only Accept visible.",
            "rule_reason": "Button contrast detected.",
            "evidence_payload": {"matched_buttons": ["Accept"]},
            "confidence": 0.85,
            "trust_impact": 10.0,
            "order_index": 0,
            "created_at": now,
        }
        finding = FindingRead(**data)
        assert finding.id == "f-001"
        assert finding.severity == "high"
        assert finding.confidence == 0.85
        assert finding.evidence_payload["matched_buttons"] == ["Accept"]
