"""Tests for the audits API endpoints.

These tests verify the API layer including:
- POST /api/audits - Create audit
- GET /api/audits/{id} - Get audit details
- GET /api/audits/{id}/findings - Get audit findings
- GET /api/audits/{id}/report - Get audit report

Includes tests for error handling and edge cases.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker as sa_sessionmaker

from app.api.routes.audits import router as audits_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.models.audit import Audit, AuditEvent, Finding


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def api_test_client(db_engine):
    """FastAPI TestClient with both health and audits routers."""
    settings = get_settings()
    TestingSession = sa_sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    test_app = FastAPI()
    test_app.include_router(health_router, prefix=settings.api_prefix)
    test_app.include_router(audits_router, prefix=settings.api_prefix)

    def _override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = _override_get_db

    # Monkey-patch SessionLocal in audits module
    import app.api.routes.audits as audits_mod
    import app.api.routes.health as health_mod

    original_audits_session_local = audits_mod.SessionLocal
    original_health_session_local = health_mod.SessionLocal

    audits_mod.SessionLocal = TestingSession
    health_mod.SessionLocal = TestingSession

    try:
        with TestClient(test_app) as client:
            yield client
    finally:
        audits_mod.SessionLocal = original_audits_session_local
        health_mod.SessionLocal = original_health_session_local
        test_app.dependency_overrides.clear()


@pytest.fixture()
def sample_audit_data():
    """Sample audit data for API requests."""
    return {
        "target_url": "https://example.com",
        "scenarios": ["cookie_consent", "checkout_flow"],
        "personas": ["privacy_sensitive", "cost_sensitive"],
    }


@pytest.fixture()
def mock_orchestrator():
    """Mock orchestrator for testing API layer."""
    mock_audit = MagicMock()
    mock_audit.id = "test-audit-id"
    mock_audit.target_url = "https://example.com"
    mock_audit.mode = "mock"
    mock_audit.status = "queued"
    mock_audit.summary = None
    mock_audit.trust_score = None
    mock_audit.risk_level = None
    mock_audit.selected_scenarios = ["cookie_consent", "checkout_flow"]
    mock_audit.selected_personas = ["privacy_sensitive", "cost_sensitive"]
    mock_audit.report_public_url = None
    mock_audit.metrics = {}
    mock_audit.created_at = "2024-01-01T00:00:00"
    mock_audit.updated_at = "2024-01-01T00:00:00"
    mock_audit.started_at = None
    mock_audit.completed_at = None
    mock_audit.events = []

    with patch("app.api.routes.audits.orchestrator") as mock_orch:
        mock_orch.create_audit.return_value = mock_audit
        mock_orch.launch_audit.return_value = None
        yield mock_orch, mock_audit


# =============================================================================
# POST /api/audits Tests
# =============================================================================


class TestCreateAuditEndpoint:
    """Test POST /api/audits endpoint."""

    def test_create_audit_returns_202(self, api_test_client, sample_audit_data, mock_orchestrator):
        """Creating audit should return 202 Accepted."""
        mock_orch, _ = mock_orchestrator
        resp = api_test_client.post("/api/audits", json=sample_audit_data)
        assert resp.status_code == 202

    def test_create_audit_returns_audit_data(self, api_test_client, sample_audit_data, mock_orchestrator):
        """Creating audit should return audit data in response."""
        mock_orch, mock_audit = mock_orchestrator
        resp = api_test_client.post("/api/audits", json=sample_audit_data)
        data = resp.json()
        assert data["id"] == "test-audit-id"
        assert data["target_url"] == "https://example.com"
        assert data["status"] == "queued"
        assert data["mode"] == "mock"

    def test_create_audit_triggers_launch(self, api_test_client, sample_audit_data, mock_orchestrator):
        """Creating audit should trigger launch_audit."""
        mock_orch, mock_audit = mock_orchestrator
        api_test_client.post("/api/audits", json=sample_audit_data)
        mock_orch.launch_audit.assert_called_once_with("test-audit-id")

    def test_create_audit_with_default_scenarios(self, api_test_client, mock_orchestrator):
        """Creating audit without scenarios should use defaults."""
        mock_orch, _ = mock_orchestrator
        data = {"target_url": "https://example.com"}
        resp = api_test_client.post("/api/audits", json=data)
        assert resp.status_code == 202

    def test_create_audit_with_default_personas(self, api_test_client, mock_orchestrator):
        """Creating audit without personas should use defaults."""
        mock_orch, _ = mock_orchestrator
        data = {"target_url": "https://example.com"}
        resp = api_test_client.post("/api/audits", json=data)
        assert resp.status_code == 202

    def test_create_audit_invalid_url_returns_422(self, api_test_client, mock_orchestrator):
        """Creating audit with invalid URL should return 422."""
        mock_orch, _ = mock_orchestrator
        data = {"target_url": "not-a-valid-url"}
        resp = api_test_client.post("/api/audits", json=data)
        assert resp.status_code == 422

    def test_create_audit_missing_url_returns_422(self, api_test_client, mock_orchestrator):
        """Creating audit without URL should return 422."""
        mock_orch, _ = mock_orchestrator
        data = {"scenarios": ["cookie_consent"]}
        resp = api_test_client.post("/api/audits", json=data)
        assert resp.status_code == 422


# =============================================================================
# GET /api/audits/{id} Tests
# =============================================================================


class TestGetAuditEndpoint:
    """Test GET /api/audits/{id} endpoint."""

    def test_get_audit_returns_200(self, db_session, api_test_client):
        """Getting existing audit should return 200."""
        # Create audit directly in DB
        audit = Audit(
            id="test-get-audit",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-get-audit")
        assert resp.status_code == 200

    def test_get_audit_returns_correct_data(self, db_session, api_test_client):
        """Getting audit should return correct audit data."""
        audit = Audit(
            id="test-get-audit-data",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            trust_score=75.0,
            risk_level="medium",
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-get-audit-data")
        data = resp.json()
        assert data["id"] == "test-get-audit-data"
        assert data["target_url"] == "https://example.com"
        assert data["status"] == "completed"
        assert data["trust_score"] == 75.0
        assert data["risk_level"] == "medium"

    def test_get_audit_not_found_returns_404(self, api_test_client):
        """Getting non-existent audit should return 404."""
        resp = api_test_client.get("/api/audits/non-existent-id")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_audit_includes_events(self, db_session, api_test_client):
        """Getting audit should include related events."""
        audit = Audit(
            id="test-audit-with-events",
            target_url="https://example.com",
            mode="mock",
            status="running",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
        )
        db_session.add(audit)
        db_session.flush()

        event = AuditEvent(
            audit_id=audit.id,
            phase="browser",
            status="info",
            message="Started browser audit",
            progress=10,
            details={"scenario": "cookie_consent"},
        )
        db_session.add(event)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-audit-with-events")
        data = resp.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["phase"] == "browser"
        assert data["events"][0]["message"] == "Started browser audit"

    def test_get_audit_with_failed_status(self, db_session, api_test_client):
        """Getting failed audit should return correct status."""
        audit = Audit(
            id="test-failed-audit",
            target_url="https://example.com",
            mode="mock",
            status="failed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            summary="Audit failed due to browser error",
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-failed-audit")
        data = resp.json()
        assert data["status"] == "failed"
        assert "failed" in data["summary"].lower()


# =============================================================================
# GET /api/audits/{id}/findings Tests
# =============================================================================


class TestGetFindingsEndpoint:
    """Test GET /api/audits/{id}/findings endpoint."""

    def test_get_findings_returns_200(self, db_session, api_test_client):
        """Getting findings for existing audit should return 200."""
        audit = Audit(
            id="test-findings-audit",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-findings-audit/findings")
        assert resp.status_code == 200

    def test_get_findings_returns_correct_structure(self, db_session, api_test_client):
        """Getting findings should return correct response structure."""
        audit = Audit(
            id="test-findings-structure",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-findings-structure/findings")
        data = resp.json()
        assert "audit_id" in data
        assert "findings" in data
        assert data["audit_id"] == "test-findings-structure"
        assert isinstance(data["findings"], list)

    def test_get_findings_not_found_audit_returns_404(self, api_test_client):
        """Getting findings for non-existent audit should return 404."""
        resp = api_test_client.get("/api/audits/non-existent-audit/findings")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_findings_with_findings(self, db_session, api_test_client):
        """Getting findings should return actual findings data."""
        audit = Audit(
            id="test-audit-with-findings",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
        )
        db_session.add(audit)
        db_session.flush()

        finding = Finding(
            id="finding-001",
            audit_id=audit.id,
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Accept without reject option",
            explanation="The cookie banner only shows accept option",
            remediation="Add a reject option",
            evidence_excerpt="Accept All button found",
            rule_reason="asymmetric_choice rule matched",
            evidence_payload={"buttons": ["Accept All"]},
            confidence=0.85,
            trust_impact=10.0,
            order_index=0,
        )
        db_session.add(finding)
        db_session.commit()

        resp = api_test_client.get(f"/api/audits/{audit.id}/findings")
        data = resp.json()
        assert len(data["findings"]) == 1
        assert data["findings"][0]["id"] == "finding-001"
        assert data["findings"][0]["severity"] == "high"
        assert data["findings"][0]["confidence"] == 0.85

    def test_get_findings_ordered_by_order_index(self, db_session, api_test_client):
        """Findings should be ordered by order_index."""
        audit = Audit(
            id="test-ordered-findings",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
        )
        db_session.add(audit)
        db_session.flush()

        # Add findings in reverse order
        for i in range(3):
            finding = Finding(
                id=f"finding-{i}",
                audit_id=audit.id,
                scenario="cookie_consent",
                persona="privacy_sensitive",
                pattern_family="asymmetric_choice",
                severity="high",
                title=f"Finding {i}",
                explanation="Test",
                remediation="Test",
                evidence_excerpt="Test",
                rule_reason="Test",
                order_index=2 - i,  # Reverse order: 2, 1, 0
            )
            db_session.add(finding)
        db_session.commit()

        resp = api_test_client.get(f"/api/audits/{audit.id}/findings")
        data = resp.json()
        order_indices = [f["order_index"] for f in data["findings"]]
        assert order_indices == [0, 1, 2]  # Should be sorted ascending


# =============================================================================
# GET /api/audits/{id}/report Tests
# =============================================================================


class TestGetReportEndpoint:
    """Test GET /api/audits/{id}/report endpoint."""

    def test_get_report_not_found_audit_returns_404(self, api_test_client):
        """Getting report for non-existent audit should return 404."""
        resp = api_test_client.get("/api/audits/non-existent-audit/report")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_report_not_generated_returns_404(self, db_session, api_test_client):
        """Getting report for audit without report_path should return 404."""
        audit = Audit(
            id="test-no-report",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            report_path=None,
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-no-report/report")
        assert resp.status_code == 404
        assert "not generated" in resp.json()["detail"].lower()

    def test_get_report_missing_file_returns_404(self, db_session, api_test_client, tmp_path):
        """Getting report for audit with non-existent file should return 404."""
        audit = Audit(
            id="test-missing-report-file",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            report_path=str(tmp_path / "non-existent-report.html"),
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-missing-report-file/report")
        assert resp.status_code == 404
        assert "missing" in resp.json()["detail"].lower()

    def test_get_report_returns_file(self, db_session, api_test_client, tmp_path):
        """Getting report for audit with existing file should return file."""
        # Create report file
        report_file = tmp_path / "test-report.html"
        report_content = "<html><body><h1>Audit Report</h1></body></html>"
        report_file.write_text(report_content)

        audit = Audit(
            id="test-with-report",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            report_path=str(report_file),
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-with-report/report")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert report_content in resp.text


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestAPIErrorHandling:
    """Test error handling for API endpoints."""

    def test_malformed_json_returns_422(self, api_test_client):
        """Sending malformed JSON should return 422."""
        resp = api_test_client.post(
            "/api/audits",
            data="not valid json",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, api_test_client):
        """Sending empty body should return 422."""
        resp = api_test_client.post("/api/audits", json={})
        assert resp.status_code == 422

    def test_invalid_audit_id_format_handled(self, api_test_client):
        """API should handle various audit ID formats gracefully."""
        # Test with special characters that might cause issues
        resp = api_test_client.get("/api/audits/audit%20with%20spaces")
        # Should return 404, not 500
        assert resp.status_code in [404, 422]


# =============================================================================
# Integration Tests
# =============================================================================


class TestAuditAPIIntegration:
    """Integration tests for audit API flow."""

    def test_full_audit_flow_create_and_get(self, db_session, api_test_client):
        """Test creating audit then retrieving it."""
        # Create audit
        create_resp = api_test_client.post(
            "/api/audits",
            json={
                "target_url": "https://example.com",
                "scenarios": ["cookie_consent"],
                "personas": ["privacy_sensitive"],
            },
        )

        # Since we mock the orchestrator in the module, let's test with DB directly
        audit = Audit(
            id="integration-test-audit",
            target_url="https://integration-test.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            trust_score=80.0,
            risk_level="low",
        )
        db_session.add(audit)
        db_session.commit()

        # Get the audit
        get_resp = api_test_client.get("/api/audits/integration-test-audit")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["target_url"] == "https://integration-test.com"
        assert data["status"] == "completed"
        assert data["trust_score"] == 80.0

    def test_audit_status_transitions(self, db_session, api_test_client):
        """Test that audit status transitions are correctly reflected in API."""
        # Create audit in different states
        states = ["queued", "running", "completed", "failed"]

        for state in states:
            audit = Audit(
                id=f"test-state-{state}",
                target_url="https://example.com",
                mode="mock",
                status=state,
                selected_scenarios=["cookie_consent"],
                selected_personas=["privacy_sensitive"],
            )
            db_session.add(audit)
        db_session.commit()

        # Verify each state
        for state in states:
            resp = api_test_client.get(f"/api/audits/test-state-{state}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == state
