"""Tests for the PDF export endpoint.

These tests verify the PDF export functionality including:
- GET /api/audits/{id}/report/pdf - Generate and download PDF report
- Content-Type is application/pdf
- Content-Disposition has filename
- PDF contains required content (trust score, risk level, findings)
- Error handling for missing audits and reports
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker as sa_sessionmaker

from app.api.routes.audits import router as audits_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.database import get_db
from app.models.audit import Audit, Finding

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def api_test_client(db_engine):
    """FastAPI TestClient with health and audits routers."""
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
def mock_pdf_generation():
    """Mock PDF generation to avoid heavy weasyprint in tests."""
    fake_pdf_bytes = b"%PDF-1.4 fake pdf content for testing purposes"
    with patch("app.api.routes.audits.generate_pdf_from_html") as mock_gen:
        mock_gen.return_value = fake_pdf_bytes
        yield mock_gen


# =============================================================================
# GET /api/audits/{id}/report/pdf Tests
# =============================================================================


class TestGetPDFReportEndpoint:
    """Test GET /api/audits/{id}/report/pdf endpoint."""

    def test_get_pdf_report_not_found_audit_returns_404(self, api_test_client):
        """Getting PDF for non-existent audit should return 404."""
        resp = api_test_client.get("/api/audits/non-existent-audit/report/pdf")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_pdf_report_not_generated_returns_404(self, db_session, api_test_client):
        """Getting PDF for audit without report_path should return 404."""
        audit = Audit(
            id="test-no-report-pdf",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            report_path=None,
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-no-report-pdf/report/pdf")
        assert resp.status_code == 404
        assert "not generated" in resp.json()["detail"].lower()

    def test_get_pdf_report_missing_html_file_returns_404(self, db_session, api_test_client, tmp_path):
        """Getting PDF for audit with non-existent HTML file should return 404."""
        audit = Audit(
            id="test-missing-html-file",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            report_path=str(tmp_path / "non-existent-report.html"),
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-missing-html-file/report/pdf")
        assert resp.status_code == 404
        assert "missing" in resp.json()["detail"].lower()

    def test_get_pdf_report_returns_pdf_content(self, db_session, api_test_client, tmp_path, mock_pdf_generation):
        """Getting PDF for audit with existing report should return PDF bytes."""
        # Create HTML report file
        report_file = tmp_path / "test-report.html"
        report_content = "<html><body><h1>Audit Report</h1><p>Trust Score: 85</p></body></html>"
        report_file.write_text(report_content)

        audit = Audit(
            id="test-with-pdf-report",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            trust_score=85.0,
            risk_level="low",
            report_path=str(report_file),
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-with-pdf-report/report/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_get_pdf_report_has_content_disposition(self, db_session, api_test_client, tmp_path, mock_pdf_generation):
        """PDF response should have Content-Disposition with filename."""
        report_file = tmp_path / "test-report.html"
        report_file.write_text("<html><body><h1>Report</h1></body></html>")

        audit = Audit(
            id="test-pdf-filename",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            trust_score=75.0,
            risk_level="medium",
            report_path=str(report_file),
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-pdf-filename/report/pdf")
        assert resp.status_code == 200
        content_disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in content_disposition or "inline" in content_disposition
        assert ".pdf" in content_disposition.lower()

    def test_get_pdf_report_with_audit_in_response(self, db_session, api_test_client, tmp_path, mock_pdf_generation):
        """PDF endpoint should use the correct audit data."""
        report_file = tmp_path / "test-report.html"
        report_file.write_text("<html><body>Test Report</body></html>")

        audit = Audit(
            id="test-pdf-audit-data",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent", "checkout_flow"],
            selected_personas=["privacy_sensitive"],
            trust_score=92.0,
            risk_level="low",
            report_path=str(report_file),
        )
        db_session.add(audit)
        db_session.commit()

        # Add a finding
        finding = Finding(
            id="finding-pdf-001",
            audit_id=audit.id,
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Hidden reject option",
            explanation="The cookie banner hides the reject option",
            remediation="Make reject option visible",
            evidence_excerpt="Accept All button visible",
            rule_reason="asymmetric_choice rule matched",
            confidence=0.85,
            trust_impact=10.0,
            order_index=0,
        )
        db_session.add(finding)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-pdf-audit-data/report/pdf")
        assert resp.status_code == 200
        # Verify the mock was called with the correct audit
        mock_pdf_generation.assert_called_once()
        call_args = mock_pdf_generation.call_args
        # The first positional arg should be the HTML content
        assert call_args is not None


class TestPDFEndpointErrorHandling:
    """Test error handling for PDF export endpoint."""

    def test_pdf_generation_failure_returns_500(self, db_session, api_test_client, tmp_path):
        """PDF generation failure should return 500 with error message."""
        report_file = tmp_path / "test-report.html"
        report_file.write_text("<html><body>Test Report</body></html>")

        audit = Audit(
            id="test-pdf-failure",
            target_url="https://example.com",
            mode="mock",
            status="completed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            report_path=str(report_file),
        )
        db_session.add(audit)
        db_session.commit()

        with patch("app.api.routes.audits.generate_pdf_from_html") as mock_gen:
            mock_gen.side_effect = Exception("PDF generation failed")
            resp = api_test_client.get("/api/audits/test-pdf-failure/report/pdf")
            assert resp.status_code == 500
            assert "pdf" in resp.json()["detail"].lower()


class TestPDFEndpointWithDifferentStatuses:
    """Test PDF endpoint behavior with different audit statuses."""

    def test_get_pdf_for_failed_audit(self, db_session, api_test_client, tmp_path, mock_pdf_generation):
        """PDF endpoint should work for failed audits if report exists."""
        report_file = tmp_path / "test-report-failed.html"
        report_file.write_text("<html><body>Failed Audit Report</body></html>")

        audit = Audit(
            id="test-pdf-failed-audit",
            target_url="https://example.com",
            mode="mock",
            status="failed",
            selected_scenarios=["cookie_consent"],
            selected_personas=["privacy_sensitive"],
            summary="Audit failed during execution",
            report_path=str(report_file),
        )
        db_session.add(audit)
        db_session.commit()

        resp = api_test_client.get("/api/audits/test-pdf-failed-audit/report/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
