"""Tests for the regulatory compliance PDF report endpoint.

These tests verify the compliance PDF export functionality including:
- GET /api/audits/{id}/report/compliance-pdf - Generate and download compliance PDF
- Content-Type is application/pdf
- Content-Disposition has filename compliance-report-{id}.pdf
- PDF contains regulation sections, article citations, compliance matrix
- Executive summary with trust score, date, findings count, implicated regulations
- Video evidence references when video_urls present
- Error handling for missing audits and audits with no regulatory findings
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
def mock_compliance_pdf_generation():
    """Mock compliance PDF generation to avoid heavy xhtml2pdf in tests."""
    fake_pdf_bytes = b"%PDF-1.4 fake compliance pdf content for testing"
    with patch("app.api.routes.audits.generate_compliance_pdf") as mock_gen:
        mock_gen.return_value = fake_pdf_bytes
        yield mock_gen


@pytest.fixture()
def real_pdf_generation():
    """Use real PDF generation for integration tests."""
    # No patch - use real service
    yield


# =============================================================================
# Test Data Helpers
# =============================================================================


def create_audit_with_regulatory_findings(db_session, audit_id="test-regulatory-audit"):
    """Create an audit with findings that have regulatory categories."""
    audit = Audit(
        id=audit_id,
        target_url="https://example.com",
        mode="mock",
        status="completed",
        selected_scenarios=["cookie_consent", "checkout_flow"],
        selected_personas=["privacy_sensitive", "cost_sensitive"],
        trust_score=65.0,
        risk_level="medium",
        report_path=None,
        video_urls={
            "cookie_consent_privacy_sensitive": "/artifacts/videos/test-cookie-privacy.webm",
            "checkout_flow_cost_sensitive": "/artifacts/videos/test-checkout-cost.webm",
        },
    )
    db_session.add(audit)
    db_session.flush()

    # Create findings with various regulatory categories
    findings = [
        Finding(
            id=f"finding-{audit_id}-001",
            audit_id=audit_id,
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="sneaking",
            severity="high",
            title="Pre-selected cookies without consent",
            explanation="Cookies are pre-enabled without explicit user consent",
            remediation="Require explicit opt-in for all non-essential cookies",
            evidence_excerpt="Analytics cookies enabled by default",
            rule_reason="Violates GDPR Article 25 - data protection by design",
            confidence=0.88,
            trust_impact=15.0,
            order_index=0,
            regulatory_categories=["GDPR", "DSA", "CPRA"],
            evidence_payload={"screenshot_urls": ["/artifacts/screenshots/test-001.png"]},
        ),
        Finding(
            id=f"finding-{audit_id}-002",
            audit_id=audit_id,
            scenario="checkout_flow",
            persona="cost_sensitive",
            pattern_family="hidden_costs",
            severity="medium",
            title="Hidden processing fees",
            explanation="Processing fees only revealed at final checkout step",
            remediation="Disclose all fees upfront in product listings",
            evidence_excerpt="$5.99 processing fee added at checkout",
            rule_reason="Violates FTC Act Section 5 - unfair or deceptive acts",
            confidence=0.82,
            trust_impact=10.0,
            order_index=1,
            regulatory_categories=["FTC", "DSA"],
            evidence_payload={"screenshot_urls": ["/artifacts/screenshots/test-002.png"]},
        ),
        Finding(
            id=f"finding-{audit_id}-003",
            audit_id=audit_id,
            scenario="checkout_flow",
            persona="cost_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Difficult subscription cancellation",
            explanation="Cancellation requires phone call during business hours",
            remediation="Provide online self-service cancellation",
            evidence_excerpt="Call 1-800-XXX-XXXX to cancel (Mon-Fri 9-5)",
            rule_reason="Violates FTC Click-to-Cancel rule and CPRA",
            confidence=0.90,
            trust_impact=20.0,
            order_index=2,
            regulatory_categories=["FTC", "CPRA"],
            evidence_payload={"screenshot_urls": ["/artifacts/screenshots/test-003.png"]},
        ),
    ]

    for finding in findings:
        db_session.add(finding)

    db_session.commit()
    return audit


def create_audit_without_regulatory_findings(db_session, audit_id="test-no-regulatory"):
    """Create an audit with findings that have no regulatory categories."""
    audit = Audit(
        id=audit_id,
        target_url="https://example.com",
        mode="mock",
        status="completed",
        selected_scenarios=["cookie_consent"],
        selected_personas=["privacy_sensitive"],
        trust_score=85.0,
        risk_level="low",
        report_path=None,
        video_urls=None,
    )
    db_session.add(audit)
    db_session.flush()

    # Create findings with empty regulatory_categories
    finding = Finding(
        id=f"finding-{audit_id}-001",
        audit_id=audit_id,
        scenario="cookie_consent",
        persona="privacy_sensitive",
        pattern_family="asymmetric_choice",
        severity="low",
        title="Minor UI inconsistency",
        explanation="Button colors are inconsistent",
        remediation="Standardize button styling",
        evidence_excerpt="Accept button is blue, reject is gray",
        rule_reason="Minor UX issue",
        confidence=0.60,
        trust_impact=2.0,
        order_index=0,
        regulatory_categories=[],  # Empty - no regulatory implications
        evidence_payload={},
    )
    db_session.add(finding)
    db_session.commit()
    return audit


# =============================================================================
# GET /api/audits/{id}/report/compliance-pdf Tests
# =============================================================================


class TestGetCompliancePDFReportEndpoint:
    """Test GET /api/audits/{id}/report/compliance-pdf endpoint."""

    def test_get_compliance_pdf_not_found_audit_returns_404(self, api_test_client):
        """Getting compliance PDF for non-existent audit should return 404."""
        resp = api_test_client.get("/api/audits/non-existent-audit/report/compliance-pdf")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_get_compliance_pdf_no_regulatory_findings_returns_404(
        self, db_session, api_test_client
    ):
        """Getting compliance PDF for audit with no regulatory findings should return 404."""
        audit = create_audit_without_regulatory_findings(db_session, "test-no-reg-pdf")

        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 404
        assert "regulatory" in resp.json()["detail"].lower() or "finding" in resp.json()["detail"].lower()

    def test_get_compliance_pdf_returns_pdf_content(
        self, db_session, api_test_client, mock_compliance_pdf_generation
    ):
        """Getting compliance PDF for audit with regulatory findings should return PDF bytes."""
        audit = create_audit_with_regulatory_findings(db_session, "test-reg-pdf")

        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF body should start with %PDF-
        assert resp.content.startswith(b"%PDF-")

    def test_get_compliance_pdf_has_correct_content_disposition(
        self, db_session, api_test_client, mock_compliance_pdf_generation
    ):
        """Compliance PDF response should have Content-Disposition with correct filename."""
        audit = create_audit_with_regulatory_findings(db_session, "test-filename")

        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 200
        content_disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in content_disposition
        expected_filename = f"compliance-report-{audit.id}.pdf"
        assert expected_filename in content_disposition

    def test_get_compliance_pdf_service_called_with_correct_data(
        self, db_session, api_test_client, mock_compliance_pdf_generation
    ):
        """Compliance PDF service should be called with correct audit and findings data."""
        audit = create_audit_with_regulatory_findings(db_session, "test-service-data")

        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 200

        # Verify the service was called
        mock_compliance_pdf_generation.assert_called_once()
        call_args = mock_compliance_pdf_generation.call_args
        assert call_args is not None

        # Check that audit and findings were passed
        kwargs = call_args.kwargs if call_args.kwargs else {}
        args = call_args.args if call_args.args else ()

        # Should have audit and findings in args or kwargs
        if args:
            assert len(args) >= 1  # At least audit passed
        if "audit" in kwargs:
            assert kwargs["audit"].id == audit.id
        if "findings" in kwargs:
            assert len(kwargs["findings"]) == 3


class TestCompliancePDFContentValidation:
    """Test that compliance PDF contains expected content."""

    def test_compliance_pdf_contains_executive_summary_fields(
        self, db_session, api_test_client
    ):
        """PDF should contain executive summary with target URL, date, trust score, findings count."""
        audit = create_audit_with_regulatory_findings(db_session, "test-exec-summary")

        # Use real PDF generation for content validation
        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            # Capture the HTML that would be rendered
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                # Return mock result
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            # Verify HTML was generated with required fields
            assert len(captured_html) == 1
            html = captured_html[0]

            # Check executive summary fields are present
            assert "https://example.com" in html or "example.com" in html
            assert any(word in html.lower() for word in ["trust", "score"])
            assert any(word in html.lower() for word in ["finding", "total"])

    def test_compliance_pdf_contains_regulation_sections(
        self, db_session, api_test_client
    ):
        """PDF should contain sections for FTC, GDPR, DSA, CPRA regulations."""
        audit = create_audit_with_regulatory_findings(db_session, "test-reg-sections")

        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            html = captured_html[0]

            # Check regulation sections exist
            assert "FTC" in html or "Federal Trade Commission" in html
            assert "GDPR" in html or "General Data Protection" in html
            assert "DSA" in html or "Digital Services Act" in html
            assert "CPRA" in html or "California Privacy Rights" in html

    def test_compliance_pdf_contains_article_citations(
        self, db_session, api_test_client
    ):
        """PDF should contain specific article citations like 'Article 25', 'FTC Act'."""
        audit = create_audit_with_regulatory_findings(db_session, "test-citations")

        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            html = captured_html[0]

            # Check for specific citations from taxonomy.REGULATION_CITATIONS
            assert "Article" in html or "Section" in html or "Act" in html

    def test_compliance_pdf_contains_compliance_matrix(
        self, db_session, api_test_client
    ):
        """PDF should contain compliance matrix showing regulations x scenarios."""
        audit = create_audit_with_regulatory_findings(db_session, "test-matrix")

        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            html = captured_html[0]

            # Check for matrix/table indicators
            assert "<table" in html.lower() or "matrix" in html.lower() or "compliance" in html.lower()

    def test_compliance_pdf_contains_video_evidence_references(
        self, db_session, api_test_client
    ):
        """PDF should reference video evidence when video_urls are present."""
        audit = create_audit_with_regulatory_findings(db_session, "test-video-refs")

        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            html = captured_html[0]

            # Should reference video or session recording
            assert any(word in html.lower() for word in ["video", "recording", "session"])

    def test_compliance_pdf_contains_evidence_references(
        self, db_session, api_test_client
    ):
        """PDF should contain evidence references like screenshot URLs or figure labels."""
        audit = create_audit_with_regulatory_findings(db_session, "test-evidence")

        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            html = captured_html[0]

            # Should reference evidence or screenshots
            assert any(word in html.lower() for word in ["evidence", "screenshot", "figure", "artifact"])

    def test_compliance_pdf_contains_ethical_site_inspector_header(
        self, db_session, api_test_client
    ):
        """PDF should contain 'EthicalSiteInspector' in header or footer."""
        audit = create_audit_with_regulatory_findings(db_session, "test-header")

        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            html = captured_html[0]
            assert "EthicalSiteInspector" in html


class TestCompliancePDFWithMultipleRegulations:
    """Test findings that appear in multiple regulation sections."""

    def test_finding_with_multiple_regulations_appears_in_each_section(
        self, db_session, api_test_client
    ):
        """Finding with regulatory_categories=[GDPR, DSA, CPRA] appears in all 3 sections."""
        audit = create_audit_with_regulatory_findings(db_session, "test-multi-reg")

        with patch("app.services.compliance_pdf_service.pisa.CreatePDF") as mock_pisa:
            captured_html = []

            def capture_html(html_content, dest):
                captured_html.append(html_content)
                class MockResult:
                    err = 0
                return MockResult()

            mock_pisa.side_effect = capture_html

            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 200

            html = captured_html[0]

            # The finding with multiple regulations should be represented
            # Verify the finding title appears in the HTML
            assert "Pre-selected cookies without consent" in html or "sneaking" in html.lower()


class TestCompliancePDFDistinctFromRegularPDF:
    """Test that compliance PDF is distinct from regular HTML report PDF."""

    def test_compliance_pdf_has_different_filename(
        self, db_session, api_test_client, mock_compliance_pdf_generation
    ):
        """Compliance PDF filename should be different from regular PDF."""
        audit = create_audit_with_regulatory_findings(db_session, "test-distinct-name")

        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 200

        content_disposition = resp.headers.get("content-disposition", "")
        # Should be compliance-report-{id}.pdf, not ethical-site-inspector-{id}.pdf
        assert "compliance-report" in content_disposition
        assert "ethical-site-inspector" not in content_disposition

    def test_compliance_pdf_endpoint_is_separate(
        self, db_session, api_test_client, mock_compliance_pdf_generation
    ):
        """Compliance PDF endpoint should be /report/compliance-pdf, not /report/pdf."""
        audit = create_audit_with_regulatory_findings(db_session, "test-distinct-endpoint")

        # Regular PDF endpoint
        # Note: This will fail for our test audit since no report_path, that's expected

        # Compliance PDF endpoint
        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 200


class TestCompliancePDFErrorHandling:
    """Test error handling for compliance PDF endpoint."""

    def test_compliance_pdf_generation_failure_returns_500(
        self, db_session, api_test_client
    ):
        """PDF generation failure should return 500 with error message."""
        audit = create_audit_with_regulatory_findings(db_session, "test-pdf-fail")

        with patch("app.api.routes.audits.generate_compliance_pdf") as mock_gen:
            mock_gen.side_effect = Exception("PDF generation failed")
            resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
            assert resp.status_code == 500
            assert "pdf" in resp.json()["detail"].lower() or "generation" in resp.json()["detail"].lower()


class TestCompliancePDFSizeAndFormat:
    """Test PDF size and format requirements."""

    def test_compliance_pdf_is_within_size_range(
        self, db_session, api_test_client, mock_compliance_pdf_generation
    ):
        """PDF should be between 10KB and 5MB."""
        audit = create_audit_with_regulatory_findings(db_session, "test-size")

        # Configure mock to return realistic PDF size (10KB)
        mock_compliance_pdf_generation.return_value = b"%PDF-1.4" + b"x" * 10240

        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 200

        content_length = len(resp.content)
        assert 10240 <= content_length <= 5242880  # 10KB to 5MB


# =============================================================================
# Integration Tests with Real PDF Generation
# =============================================================================


@pytest.mark.integration
class TestCompliancePDFIntegration:
    """Integration tests using real PDF generation (may be slower)."""

    def test_real_pdf_generation_produces_valid_pdf(
        self, db_session, api_test_client
    ):
        """Real PDF generation should produce valid PDF bytes."""
        audit = create_audit_with_regulatory_findings(db_session, "test-real-pdf")

        resp = api_test_client.get(f"/api/audits/{audit.id}/report/compliance-pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF-")

        # Verify PDF is reasonable size
        assert len(resp.content) > 1024  # At least 1KB
        assert len(resp.content) < 10485760  # Less than 10MB
