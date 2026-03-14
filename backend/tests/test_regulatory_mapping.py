"""
Tests for regulatory mapping integration with the audit orchestrator.

These tests verify that:
1. Findings have regulatory_categories populated from taxonomy
2. FindingRead schema includes regulatory_categories and suppressed fields
3. Audit metrics include suppressed_count
4. Evidence payload includes evidence_type field
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.audit import Finding
from app.schemas.audit import FindingRead


class TestFindingModelRegulatoryFields:
    """Test that Finding model has regulatory_categories and suppressed fields."""

    def test_finding_model_has_regulatory_categories(self, db_session):
        """Finding model should have regulatory_categories field."""
        finding = Finding(
            audit_id="test-audit-id",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Test Finding",
            explanation="Test explanation",
            remediation="Test remediation",
            evidence_excerpt="Test evidence",
            rule_reason="Test rule",
            regulatory_categories=["FTC", "DSA"],
            suppressed=False,
        )
        db_session.add(finding)
        db_session.commit()

        # Refresh and verify
        db_session.refresh(finding)
        assert finding.regulatory_categories == ["FTC", "DSA"]
        assert finding.suppressed is False

    def test_finding_model_regulatory_categories_default_empty(self, db_session):
        """Finding model should have empty list as default for regulatory_categories."""
        finding = Finding(
            audit_id="test-audit-id",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Test Finding",
            explanation="Test explanation",
            remediation="Test remediation",
            evidence_excerpt="Test evidence",
            rule_reason="Test rule",
        )
        db_session.add(finding)
        db_session.commit()

        db_session.refresh(finding)
        assert finding.regulatory_categories == []

    def test_finding_model_suppressed_default_false(self, db_session):
        """Finding model should have False as default for suppressed."""
        finding = Finding(
            audit_id="test-audit-id",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Test Finding",
            explanation="Test explanation",
            remediation="Test remediation",
            evidence_excerpt="Test evidence",
            rule_reason="Test rule",
        )
        db_session.add(finding)
        db_session.commit()

        db_session.refresh(finding)
        assert finding.suppressed is False

    def test_finding_model_can_set_suppressed_true(self, db_session):
        """Finding model should allow setting suppressed to True."""
        finding = Finding(
            audit_id="test-audit-id",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Test Finding",
            explanation="Test explanation",
            remediation="Test remediation",
            evidence_excerpt="Test evidence",
            rule_reason="Test rule",
            suppressed=True,
        )
        db_session.add(finding)
        db_session.commit()

        db_session.refresh(finding)
        assert finding.suppressed is True


class TestFindingReadSchema:
    """Test that FindingRead schema includes new fields."""

    def test_finding_read_has_regulatory_categories(self):
        """FindingRead should include regulatory_categories field."""
        finding_data = {
            "id": "test-id",
            "scenario": "cookie_consent",
            "persona": "privacy_sensitive",
            "pattern_family": "asymmetric_choice",
            "severity": "high",
            "title": "Test Title",
            "explanation": "Test explanation",
            "remediation": "Test remediation",
            "evidence_excerpt": "Test evidence",
            "rule_reason": "Test rule",
            "evidence_payload": {},
            "confidence": 0.85,
            "trust_impact": 10.0,
            "order_index": 1,
            "created_at": datetime.now(UTC),
            "regulatory_categories": ["FTC", "DSA"],
            "suppressed": False,
        }
        finding_read = FindingRead.model_validate(finding_data)
        assert finding_read.regulatory_categories == ["FTC", "DSA"]

    def test_finding_read_regulatory_categories_defaults_to_empty_list(self):
        """FindingRead should default regulatory_categories to empty list."""
        finding_data = {
            "id": "test-id",
            "scenario": "cookie_consent",
            "persona": "privacy_sensitive",
            "pattern_family": "asymmetric_choice",
            "severity": "high",
            "title": "Test Title",
            "explanation": "Test explanation",
            "remediation": "Test remediation",
            "evidence_excerpt": "Test evidence",
            "rule_reason": "Test rule",
            "evidence_payload": {},
            "confidence": 0.85,
            "trust_impact": 10.0,
            "order_index": 1,
            "created_at": datetime.now(UTC),
        }
        finding_read = FindingRead.model_validate(finding_data)
        assert finding_read.regulatory_categories == []

    def test_finding_read_has_suppressed_field(self):
        """FindingRead should include suppressed field."""
        finding_data = {
            "id": "test-id",
            "scenario": "cookie_consent",
            "persona": "privacy_sensitive",
            "pattern_family": "asymmetric_choice",
            "severity": "high",
            "title": "Test Title",
            "explanation": "Test explanation",
            "remediation": "Test remediation",
            "evidence_excerpt": "Test evidence",
            "rule_reason": "Test rule",
            "evidence_payload": {},
            "confidence": 0.85,
            "trust_impact": 10.0,
            "order_index": 1,
            "created_at": datetime.now(UTC),
            "suppressed": True,
        }
        finding_read = FindingRead.model_validate(finding_data)
        assert finding_read.suppressed is True

    def test_finding_read_suppressed_defaults_to_false(self):
        """FindingRead should default suppressed to False."""
        finding_data = {
            "id": "test-id",
            "scenario": "cookie_consent",
            "persona": "privacy_sensitive",
            "pattern_family": "asymmetric_choice",
            "severity": "high",
            "title": "Test Title",
            "explanation": "Test explanation",
            "remediation": "Test remediation",
            "evidence_excerpt": "Test evidence",
            "rule_reason": "Test rule",
            "evidence_payload": {},
            "confidence": 0.85,
            "trust_impact": 10.0,
            "order_index": 1,
            "created_at": datetime.now(UTC),
        }
        finding_read = FindingRead.model_validate(finding_data)
        assert finding_read.suppressed is False


class TestOrchestratorIntegration:
    """Test regulatory mapping integration with audit orchestrator."""

    @pytest.fixture
    def orchestrator_with_stub(self, db_engine):
        """Create an orchestrator with a stubbed browser provider."""
        from sqlalchemy.orm import sessionmaker

        from app.schemas.runtime import BrowserRunResult, JourneyObservation, ObservationEvidence
        from app.services.audit_orchestrator import AuditOrchestrator

        session_local = sessionmaker(bind=db_engine)
        orchestrator = AuditOrchestrator(session_local)

        # Stub provider that returns a finding-generating observation
        class RegulatoryTestStubBrowserProvider:
            def __init__(self):
                self.run_audit_called = False

            def run_audit(self, audit_id, target_url, scenarios, personas, progress):
                self.run_audit_called = True
                observations = []
                for scenario in scenarios:
                    for persona in personas:
                        observations.append(
                            JourneyObservation(
                                scenario=scenario,
                                persona=persona,
                                target_url=target_url,
                                final_url=target_url,
                                evidence=ObservationEvidence(
                                    screenshot_urls=[],
                                    screenshot_paths=[],
                                    button_labels=["Accept All"],  # No reject = asymmetric
                                    checkbox_states={},
                                    price_points=[],
                                    text_snippets=["Accept cookies to continue"],
                                    headings=["Cookie Consent"],
                                    page_title="Cookie Settings",
                                    dom_excerpt="Banner with accept button",
                                    step_count=1,
                                    friction_indicators=["Asymmetric choice"],
                                    activity_log=["Loaded page", "Found banner"],
                                    metadata={
                                        "source": "stub",
                                        "source_label": "Test stub",
                                        "site_host": "example.com",
                                        "scenario_state_found": True,
                                        "action_count": 1,
                                    },
                                ),
                            )
                        )
                return BrowserRunResult(
                    observations=observations,
                    summary={
                        "mode": "stub",
                        "evidence_origin_label": "Test stub provider",
                        "observation_count": len(observations),
                    },
                )

        stub_provider = RegulatoryTestStubBrowserProvider()
        stub_classifier = MagicMock()
        stub_classifier.classify = MagicMock(return_value=MagicMock(
            severity="high",
            explanation="Test explanation",
            remediation="Test remediation",
            confidence=0.80,
        ))

        with (
            patch("app.services.audit_orchestrator.get_browser_provider", return_value=stub_provider),
            patch("app.services.audit_orchestrator.get_classifier_provider", return_value=stub_classifier),
            patch("app.services.audit_orchestrator.get_fallback_browser_provider", return_value=stub_provider),
            patch(
                "app.services.report_service.ReportService.generate_report",
                return_value=("C:/report.html", "/reports/test.html"),
            ),
        ):
            yield orchestrator, stub_provider

    def test_findings_have_regulatory_categories_after_audit(self, db_session, orchestrator_with_stub):
        """VAL-ADV-001: Findings should have regulatory_categories populated after audit."""
        import time

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = orchestrator_with_stub

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        # Run audit
        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        # Refresh and check findings
        db_session.refresh(audit)
        findings = db_session.query(Finding).filter(Finding.audit_id == audit_id).all()

        # Should have findings with regulatory_categories
        assert len(findings) > 0
        for finding in findings:
            assert hasattr(finding, 'regulatory_categories')
            assert isinstance(finding.regulatory_categories, list)
            # Asymmetric choice should have FTC and DSA
            if finding.pattern_family == "asymmetric_choice":
                assert "FTC" in finding.regulatory_categories
                assert "DSA" in finding.regulatory_categories

    def test_findings_have_evidence_type_in_payload(self, db_session, orchestrator_with_stub):
        """Findings should have evidence_type in evidence_payload after audit."""
        import time

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = orchestrator_with_stub

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)
        findings = db_session.query(Finding).filter(Finding.audit_id == audit_id).all()

        assert len(findings) > 0
        for finding in findings:
            assert "evidence_type" in finding.evidence_payload
            assert finding.evidence_payload["evidence_type"] in ["nova_ai", "heuristic", "rule_based", "mock"]

    def test_findings_have_evidence_type_label(self, db_session, orchestrator_with_stub):
        """Findings should have human-readable evidence_type_label in payload."""
        import time

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = orchestrator_with_stub

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)
        findings = db_session.query(Finding).filter(Finding.audit_id == audit_id).all()

        assert len(findings) > 0
        for finding in findings:
            assert "evidence_type_label" in finding.evidence_payload
            assert isinstance(finding.evidence_payload["evidence_type_label"], str)
            assert len(finding.evidence_payload["evidence_type_label"]) > 0

    def test_audit_metrics_include_suppressed_count(self, db_session, orchestrator_with_stub):
        """VAL-ADV-005: Audit metrics should include suppressed_count."""
        import time

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = orchestrator_with_stub

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)

        assert "suppressed_count" in audit.metrics
        assert isinstance(audit.metrics["suppressed_count"], int)
        assert audit.metrics["suppressed_count"] >= 0

    def test_audit_metrics_include_active_finding_count(self, db_session, orchestrator_with_stub):
        """Audit metrics should include active_finding_count (non-suppressed)."""
        import time

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        orchestrator, _ = orchestrator_with_stub

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)

        assert "active_finding_count" in audit.metrics
        assert isinstance(audit.metrics["active_finding_count"], int)
        assert audit.metrics["active_finding_count"] >= 0
        # active = total - suppressed
        expected_active = audit.metrics["finding_count"] - audit.metrics["suppressed_count"]
        assert audit.metrics["active_finding_count"] == expected_active

    def test_confidence_scoring_nova_ai_vs_heuristic(self, db_session):
        """VAL-ADV-003: Nova AI findings get confidence > 0.75, heuristic <= 0.75."""
        from app.detectors.suppression import calculate_confidence

        # Nova AI evidence should get confidence > 0.75
        nova_ai_confidence = calculate_confidence(
            evidence_type="nova_ai",
            has_ai_evidence=True,
            has_heuristic_evidence=False,
            pattern_family="asymmetric_choice",
            evidence_payload={"screenshot_paths": ["/path/to/screenshot.png"]},
        )
        assert nova_ai_confidence > 0.75, f"Nova AI confidence {nova_ai_confidence} should be > 0.75"

        # Heuristic-only should get confidence <= 0.75
        heuristic_confidence = calculate_confidence(
            evidence_type="heuristic",
            has_ai_evidence=False,
            has_heuristic_evidence=True,
            pattern_family="asymmetric_choice",
            evidence_payload={"matched_buttons": ["Accept"]},
        )
        assert heuristic_confidence <= 0.75, f"Heuristic confidence {heuristic_confidence} should be <= 0.75"


class TestRegulatoryMappingValidationContract:
    """Tests for validation contract assertions VAL-ADV-001 through VAL-ADV-008."""

    def test_val_adv_001_regulatory_mapping_data_exists(self, db_session):
        """VAL-ADV-001: Regulatory mapping data exists on findings."""
        finding = Finding(
            audit_id="test-audit-id",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Test Finding",
            explanation="Test explanation",
            remediation="Test remediation",
            evidence_excerpt="Test evidence",
            rule_reason="Test rule",
            regulatory_categories=["FTC", "DSA"],
        )
        db_session.add(finding)
        db_session.commit()

        # Verify via FindingRead schema
        finding_read = FindingRead.model_validate(finding)
        assert finding_read.regulatory_categories is not None
        assert len(finding_read.regulatory_categories) > 0

    def test_val_adv_003_confidence_scoring_data_exists(self, db_session):
        """VAL-ADV-003: Findings have confidence scores and evidence types."""
        finding = Finding(
            audit_id="test-audit-id",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Test Finding",
            explanation="Test explanation",
            remediation="Test remediation",
            evidence_excerpt="Test evidence",
            rule_reason="Test rule",
            evidence_payload={"evidence_type": "heuristic", "evidence_type_label": "Heuristic detection"},
            confidence=0.65,
        )
        db_session.add(finding)
        db_session.commit()

        finding_read = FindingRead.model_validate(finding)
        assert finding_read.confidence > 0
        assert finding_read.confidence <= 1.0
        assert finding_read.evidence_payload.get("evidence_type") is not None

    def test_val_adv_005_false_positive_suppression_data_exists(self, db_session):
        """VAL-ADV-005: Findings have suppressed flag for false positives."""
        finding = Finding(
            audit_id="test-audit-id",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            pattern_family="asymmetric_choice",
            severity="high",
            title="Test Finding",
            explanation="Test explanation",
            remediation="Test remediation",
            evidence_excerpt="Test evidence",
            rule_reason="Test rule",
            suppressed=True,
            evidence_payload={"suppressed": True, "suppression_reason": "legitimate_cookie_consent_equal_options"},
        )
        db_session.add(finding)
        db_session.commit()

        finding_read = FindingRead.model_validate(finding)
        assert finding_read.suppressed is True
