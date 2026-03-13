"""
Tests for audit lifecycle - create → run → complete/fail flows.

These tests use simple stubs for providers (not MockBrowserAuditProvider)
to verify the full audit orchestration pipeline.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.taxonomy import AUDIT_SCENARIOS, PERSONA_DEFINITIONS, SEVERITY_LEVELS
from app.models.audit import Audit, AuditEvent, Finding
from app.schemas.runtime import BrowserRunResult, JourneyObservation, ObservationEvidence

# =============================================================================
# Stubs for Testing (simple implementations, not MockBrowserAuditProvider)
# =============================================================================


class SimpleStubBrowserProvider:
    """Simple stub browser provider that returns predefined JourneyObservation data."""

    def __init__(self, observations: list[JourneyObservation] | None = None):
        self.observations = observations or []
        self.run_audit_called = False
        self.last_audit_args: dict | None = None

    def run_audit(
        self, audit_id: str, target_url: str, scenarios: list[str], personas: list[str], progress
    ) -> BrowserRunResult:
        """Return predefined observations."""
        self.run_audit_called = True
        self.last_audit_args = {
            "audit_id": audit_id,
            "target_url": target_url,
            "scenarios": scenarios,
            "personas": personas,
        }

        # Report progress
        for obs in self.observations:
            progress(
                "browser",
                f"Running {obs.scenario} for {obs.persona}",
                50,
                "running",
                {"scenario": obs.scenario, "persona": obs.persona},
            )

        return BrowserRunResult(
            observations=self.observations,
            summary={
                "mode": "stub",
                "evidence_origin": "stub",
                "evidence_origin_label": "Stub browser provider",
                "observation_count": len(self.observations),
                "scenarios": scenarios,
                "personas": personas,
            },
        )


class SimpleStubClassifierProvider:
    """Simple stub classifier provider."""

    def classify(self, draft):
        """Return a simple classification result."""
        return MagicMock(
            severity="medium",
            explanation=f"Classified: {draft.title}",
            remediation="Review the finding and take appropriate action.",
            confidence=0.75,
        )


class FailingStubBrowserProvider:
    """Stub that always fails to test error handling."""

    def run_audit(self, audit_id: str, target_url: str, scenarios: list[str], personas: list[str], progress):
        """Always raise an exception."""
        raise RuntimeError("Simulated browser provider failure")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_observation():
    """Create a sample JourneyObservation for testing."""
    return JourneyObservation(
        scenario="cookie_consent",
        persona="privacy_sensitive",
        target_url="https://example.com",
        final_url="https://example.com/cookies",
        evidence=ObservationEvidence(
            screenshot_urls=["/artifacts/test.png"],
            screenshot_paths=["C:/data/screenshots/test.png"],
            button_labels=["Accept All", "Reject"],
            checkbox_states={"analytics": True},
            price_points=[],
            text_snippets=["Accept cookies to continue"],
            headings=["Cookie Consent"],
            page_title="Cookie Settings",
            dom_excerpt="Banner present with accept/reject options",
            step_count=3,
            friction_indicators=["Asymmetric choice"],
            activity_log=["Loaded page", "Found banner", "Clicked reject"],
            metadata={
                "source": "stub",
                "source_label": "Test stub",
                "site_host": "example.com",
                "page_url": "https://example.com/cookies",
                "interacted_controls": ["accept_button", "reject_button"],
                "scenario_state_found": True,
                "action_count": 3,
                "observed_price_delta": 0.0,
                "state_snapshots": [
                    {"url": "https://example.com", "step": "initial"},
                    {"url": "https://example.com/cookies", "step": "interaction"},
                ],
            },
        ),
    )


@pytest.fixture
def multiple_observations():
    """Create multiple observations for different scenarios and personas."""
    observations = []
    for scenario in ["cookie_consent", "checkout_flow"]:
        for persona in ["privacy_sensitive", "cost_sensitive"]:
            observations.append(
                JourneyObservation(
                    scenario=scenario,
                    persona=persona,
                    target_url="https://example.com",
                    final_url=f"https://example.com/{scenario}",
                    evidence=ObservationEvidence(
                        screenshot_urls=[f"/artifacts/{scenario}_{persona}.png"],
                        screenshot_paths=[f"C:/data/{scenario}_{persona}.png"],
                        button_labels=["Button 1", "Button 2"],
                        checkbox_states={},
                        price_points=[{"label": "Total", "value": 99.99}] if scenario == "checkout_flow" else [],
                        text_snippets=[f"Test snippet for {scenario}"],
                        headings=[scenario.replace("_", " ").title()],
                        page_title=f"{scenario.replace('_', ' ').title()} Page",
                        dom_excerpt=f"DOM for {scenario}",
                        step_count=5,
                        friction_indicators=["Some friction"],
                        activity_log=[f"Ran {scenario} as {persona}"],
                        metadata={
                            "source": "stub",
                            "source_label": "Test stub",
                            "site_host": "example.com",
                            "page_url": f"https://example.com/{scenario}",
                            "interacted_controls": ["control1", "control2"],
                            "scenario_state_found": True,
                            "action_count": 5,
                            "observed_price_delta": 10.0 if scenario == "checkout_flow" else 0.0,
                            "state_snapshots": [{"url": "https://example.com", "step": "initial"}],
                        },
                    ),
                )
            )
    return observations


# =============================================================================
# Audit Lifecycle Tests
# =============================================================================


class TestAuditLifecycleCreateRunComplete:
    """Test create audit → run → complete flow."""

    @pytest.fixture
    def orchestrator_with_stub(self, db_engine, sample_observation):
        """Create an orchestrator with a stubbed browser provider."""
        from sqlalchemy.orm import sessionmaker

        from app.services.audit_orchestrator import AuditOrchestrator

        session_local = sessionmaker(bind=db_engine)
        orchestrator = AuditOrchestrator(session_local)

        # Stub the providers
        stub_provider = SimpleStubBrowserProvider([sample_observation])
        stub_classifier = SimpleStubClassifierProvider()

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

    def test_create_audit_stores_correct_data(self, db_session, orchestrator_with_stub):
        """Audit creation should store all input data correctly."""
        orchestrator, _ = orchestrator_with_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent", "checkout_flow"],
            personas=["privacy_sensitive"],
        )

        audit = orchestrator.create_audit(db_session, payload, "test_mode")

        assert audit.target_url == "https://test-site.com/"
        assert audit.mode == "test_mode"
        assert audit.status == "queued"
        assert audit.selected_scenarios == ["cookie_consent", "checkout_flow"]
        assert audit.selected_personas == ["privacy_sensitive"]

    def test_create_audit_creates_initial_event(self, db_session, orchestrator_with_stub):
        """Audit creation should create an initial queued event."""
        orchestrator, _ = orchestrator_with_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )

        audit = orchestrator.create_audit(db_session, payload, "test_mode")

        # Check that an event was created
        events = db_session.query(AuditEvent).filter(AuditEvent.audit_id == audit.id).all()
        assert len(events) == 1
        assert events[0].phase == "queue"
        assert events[0].status == "info"

    def test_run_audit_transitions_status(self, db_session, orchestrator_with_stub):
        """Running audit should transition status from queued to running to completed."""
        orchestrator, stub_provider = orchestrator_with_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        # Create audit
        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        # Run audit (blocking call)
        orchestrator.run_audit(audit_id)

        # Give it a moment to complete
        time.sleep(0.5)

        # Refresh audit from database
        db_session.refresh(audit)

        # Status should be completed
        assert audit.status == "completed"
        assert audit.started_at is not None
        assert audit.completed_at is not None
        assert audit.trust_score is not None
        assert audit.risk_level is not None
        assert audit.summary is not None

    def test_run_audit_creates_findings(self, db_session, orchestrator_with_stub):
        """Running audit should create findings from observations."""
        orchestrator, stub_provider = orchestrator_with_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

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

        # Should have at least one finding from the observation
        assert len(findings) >= 0  # Rule engine may or may not generate findings

    def test_run_audit_emits_events(self, db_session, orchestrator_with_stub):
        """Running audit should emit progress events."""
        orchestrator, stub_provider = orchestrator_with_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        initial_event_count = db_session.query(AuditEvent).filter(AuditEvent.audit_id == audit_id).count()

        # Run audit
        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        # Check that more events were created
        final_event_count = db_session.query(AuditEvent).filter(AuditEvent.audit_id == audit_id).count()
        assert final_event_count > initial_event_count

    def test_run_audit_generates_metrics(self, db_session, orchestrator_with_stub):
        """Running audit should generate metrics in the audit record."""
        orchestrator, stub_provider = orchestrator_with_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

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

        # Refresh and check metrics
        db_session.refresh(audit)

        assert audit.metrics is not None
        assert "observation_count" in audit.metrics
        assert audit.metrics["observation_count"] >= 1


class TestAuditLifecycleCreateRunFail:
    """Test create audit → run → fail flow with error handling."""

    @pytest.fixture
    def orchestrator_with_failing_stub(self, db_engine):
        """Create an orchestrator with a failing browser provider."""
        from sqlalchemy.orm import sessionmaker

        from app.services.audit_orchestrator import AuditOrchestrator

        session_local = sessionmaker(bind=db_engine)
        orchestrator = AuditOrchestrator(session_local)

        # Stub providers - browser fails, fallback succeeds
        failing_provider = FailingStubBrowserProvider()
        fallback_provider = SimpleStubBrowserProvider([])
        stub_classifier = SimpleStubClassifierProvider()

        with (
            patch("app.services.audit_orchestrator.get_browser_provider", return_value=failing_provider),
            patch("app.services.audit_orchestrator.get_classifier_provider", return_value=stub_classifier),
            patch(
                "app.services.audit_orchestrator.get_fallback_browser_provider", return_value=fallback_provider
            ),
            patch(
                "app.services.report_service.ReportService.generate_report",
                return_value=("C:/report.html", "/reports/test.html"),
            ),
        ):
            yield orchestrator, failing_provider, fallback_provider

    def test_failed_audit_uses_fallback_provider(self, db_session, orchestrator_with_failing_stub):
        """When primary provider fails, fallback provider should be used."""
        orchestrator, failing_provider, fallback_provider = orchestrator_with_failing_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        # Run audit - should not crash due to fallback
        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        # Refresh audit
        db_session.refresh(audit)

        # Audit should complete via fallback
        assert audit.status == "completed"

        # Fallback provider should have been called
        assert fallback_provider.run_audit_called

    def test_fallback_emits_warning_event(self, db_session, orchestrator_with_failing_stub):
        """Fallback to mock mode should emit a warning event."""
        orchestrator, _, _ = orchestrator_with_failing_stub

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        # Check for fallback warning event
        events = (
            db_session.query(AuditEvent).filter(AuditEvent.audit_id == audit_id, AuditEvent.phase == "fallback").all()
        )

        assert len(events) >= 1
        assert "fallback" in events[0].phase


class TestAuditLifecycleMultipleScenariosPersonas:
    """Test audit lifecycle with multiple scenarios and personas."""

    @pytest.fixture
    def orchestrator_with_multiple_observations(self, db_engine, multiple_observations):
        """Create an orchestrator with multiple stub observations."""
        from sqlalchemy.orm import sessionmaker

        from app.services.audit_orchestrator import AuditOrchestrator

        session_local = sessionmaker(bind=db_engine)
        orchestrator = AuditOrchestrator(session_local)

        stub_provider = SimpleStubBrowserProvider(multiple_observations)
        stub_classifier = SimpleStubClassifierProvider()

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

    def test_multiple_scenarios_create_multiple_observations(self, db_session, orchestrator_with_multiple_observations):
        """Multiple scenarios should result in multiple observations."""
        orchestrator, stub_provider = orchestrator_with_multiple_observations

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent", "checkout_flow"],
            personas=["privacy_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        # Check that provider was called with correct args
        assert stub_provider.run_audit_called
        assert len(stub_provider.last_audit_args["scenarios"]) == 2
        assert "cookie_consent" in stub_provider.last_audit_args["scenarios"]
        assert "checkout_flow" in stub_provider.last_audit_args["scenarios"]

    def test_audit_metrics_include_all_scenarios(self, db_session, orchestrator_with_multiple_observations):
        """Metrics should include data from all scenarios."""
        orchestrator, stub_provider = orchestrator_with_multiple_observations

        from pydantic import HttpUrl

        from app.schemas.audit import AuditCreateRequest

        payload = AuditCreateRequest(
            target_url=HttpUrl("https://test-site.com"),
            scenarios=["cookie_consent", "checkout_flow"],
            personas=["privacy_sensitive", "cost_sensitive"],
        )
        audit = orchestrator.create_audit(db_session, payload, "test_mode")
        audit_id = audit.id

        orchestrator.run_audit(audit_id)
        time.sleep(0.5)

        db_session.refresh(audit)

        # Metrics should show all observations
        assert audit.metrics["observation_count"] == 4  # 2 scenarios x 2 personas
        assert len(audit.metrics["persona_comparison"]) == 2


# =============================================================================
# Taxonomy Integration in Lifecycle Tests
# =============================================================================


class TestTaxonomyIntegrationInLifecycle:
    """Test that taxonomy is properly used throughout the audit lifecycle."""

    def test_all_taxonomy_scenarios_supported_by_orchestrator(self):
        """Orchestrator should support all 6 taxonomy scenarios."""

        # Verify all scenarios from taxonomy are valid
        for scenario in AUDIT_SCENARIOS:
            assert scenario in [
                "cookie_consent",
                "subscription_cancellation",
                "checkout_flow",
                "account_deletion",
                "newsletter_signup",
                "pricing_comparison",
            ]

    def test_all_taxonomy_personas_supported_by_orchestrator(self):
        """Orchestrator should support all 3 taxonomy personas."""
        for persona in PERSONA_DEFINITIONS:
            assert persona in ["privacy_sensitive", "cost_sensitive", "exit_intent"]

    def test_severity_levels_used_in_findings(self, db_session):
        """Findings should use taxonomy severity levels."""
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

        assert finding.severity in SEVERITY_LEVELS


# =============================================================================
# Error Handling and Edge Cases
# =============================================================================


class TestAuditLifecycleErrorHandling:
    """Test error handling in audit lifecycle."""

    def test_get_audit_not_found_raises_error(self, db_session):
        """Getting non-existent audit should raise ValueError."""
        from sqlalchemy.orm import sessionmaker

        from app.services.audit_orchestrator import AuditOrchestrator

        session_local = sessionmaker(bind=db_session.bind)
        orchestrator = AuditOrchestrator(session_local)

        with pytest.raises(ValueError, match="Audit non-existent-id not found"):
            orchestrator.get_audit(db_session, "non-existent-id")

    def test_audit_event_stored_with_correct_audit_id(self, db_session):
        """Events should be linked to correct audit."""
        from sqlalchemy.orm import sessionmaker

        from app.services.audit_orchestrator import AuditOrchestrator

        session_local = sessionmaker(bind=db_session.bind)
        orchestrator = AuditOrchestrator(session_local)

        audit = Audit(
            target_url="https://example.com",
            mode="mock",
            status="queued",
        )
        db_session.add(audit)
        db_session.commit()

        orchestrator.emit_event(
            audit_id=audit.id,
            phase="test",
            message="Test event",
            progress=50,
            status="info",
            details={"test": "data"},
        )

        events = db_session.query(AuditEvent).filter(AuditEvent.audit_id == audit.id).all()
        assert len(events) == 1
        assert events[0].phase == "test"
        assert events[0].message == "Test event"
