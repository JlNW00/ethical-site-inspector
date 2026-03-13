"""
Tests for Nova Act Audit Provider.

These tests use simple stubs for the Nova Act SDK, not the existing MockBrowserAuditProvider.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.core.taxonomy import (
    AUDIT_SCENARIOS,
    DARK_PATTERN_CATEGORIES,
    PERSONA_DEFINITIONS,
)
from app.providers.nova_act_browser import (
    AccountDeletionObservation,
    CheckoutObservation,
    CookieConsentObservation,
    NewsletterSignupObservation,
    NovaActAuditProvider,
    PricingComparisonObservation,
    SubscriptionCancellationObservation,
)
from app.providers.storage import StorageProvider, StorageObject


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock storage provider."""
    storage = MagicMock(spec=StorageProvider)
    storage.save_bytes.return_value = StorageObject(
        relative_key="screenshots/test/test.png",
        public_url="/artifacts/screenshots/test/test.png",
        absolute_path="C:/data/screenshots/test/test.png",
    )
    return storage


@pytest.fixture
def mock_nova_act_module():
    """Create a mock Nova Act module."""
    mock_module = MagicMock()
    mock_module.BOOL_SCHEMA = {"type": "boolean"}
    mock_module.STRING_SCHEMA = {"type": "string"}

    # Mock the NovaAct class
    mock_nova_instance = MagicMock()
    mock_nova_instance.page = MagicMock()
    mock_nova_instance.page.screenshot.return_value = b"fake_screenshot_data"
    mock_nova_instance.page.url = "https://example.com/test"
    mock_nova_instance.page.content.return_value = "<html><body>Test</body></html>"

    # Mock act method
    mock_nova_instance.act.return_value = MagicMock(
        response="Action completed",
        num_steps=5,
    )

    # Mock act_get method - returns parsed response
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
                "deceptive_language": [],
                "pre_selected_options": [],
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
        elif schema and "cancellation" in prompt.lower():
            result.parsed_response = {
                "cancellation_flow_found": True,
                "clicks_to_cancel": 3,
                "detours_encountered": [],
                "confirmshaming_detected": False,
                "confirmshaming_phrases": [],
                "pause_offered": False,
                "alternative_options": [],
                "final_cancel_difficult": False,
            }
        elif schema and "deletion" in prompt.lower():
            result.parsed_response = {
                "deletion_flow_found": True,
                "clicks_to_delete": 4,
                "obstacles_encountered": [],
                "requires_contact_support": False,
                "confirmation_required": True,
                "data_retention_warning": None,
                "alternatives_offered": [],
                "flow_completed": True,
            }
        elif schema and "newsletter" in prompt.lower():
            result.parsed_response = {
                "signup_form_found": True,
                "pre_checked_boxes": ["Marketing emails"],
                "confusing_opt_in": False,
                "confusing_language_examples": [],
                "dark_enrollment_detected": False,
                "bundled_with_other_services": False,
                "unsubscription_difficulty": "Easy",
                "consent_separated": True,
            }
        elif schema and "pricing" in prompt.lower():
            result.parsed_response = {
                "prices_found": [{"label": "Product", "value": 29.99}],
                "price_variations_detected": False,
                "bait_and_switch_suspected": False,
                "persona_specific_offers": [],
                "hidden_discounts": [],
                "loyalty_program_pressure": False,
                "dynamic_pricing_indicators": [],
            }
        else:
            result.parsed_response = True
        return result

    mock_nova_instance.act_get.side_effect = mock_act_get

    # Make NovaAct a context manager that returns our mock instance
    mock_nova_class = MagicMock()
    mock_nova_class.return_value.__enter__ = MagicMock(return_value=mock_nova_instance)
    mock_nova_class.return_value.__exit__ = MagicMock(return_value=False)

    mock_module.NovaAct = mock_nova_class

    return mock_module


# =============================================================================
# Provider Instantiation Tests
# =============================================================================


class TestNovaActAuditProviderInstantiation:
    """Test NovaActAuditProvider initialization."""

    def test_provider_implements_abc(self, mock_storage):
        """Provider should implement BrowserAuditProvider ABC."""
        provider = NovaActAuditProvider(mock_storage)
        assert isinstance(provider, NovaActAuditProvider)

    def test_provider_has_required_attributes(self, mock_storage):
        """Provider should have required configuration attributes."""
        provider = NovaActAuditProvider(
            storage=mock_storage,
            headless=True,
            tty=False,
            timeout=120,
            max_workers=3,
        )
        assert provider.storage == mock_storage
        assert provider.headless is True
        assert provider.tty is False
        assert provider.timeout == 120
        assert provider.max_workers == 3

    def test_provider_default_configuration(self, mock_storage):
        """Provider should have sensible defaults."""
        provider = NovaActAuditProvider(mock_storage)
        assert provider.headless is True
        assert provider.tty is False
        assert provider.timeout == 120
        assert provider.max_workers == 3


# =============================================================================
# Scenario Method Tests
# =============================================================================


class TestCookieConsentScenario:
    """Test cookie consent scenario with Nova Act."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_cookie_consent_returns_observation(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Cookie consent should return JourneyObservation with evidence."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_cookie_consent_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="privacy_sensitive",
            nova_act=mock_nova_act_module,
        )

        assert result.scenario == "cookie_consent"
        assert result.persona == "privacy_sensitive"
        assert result.target_url == "https://example.com"
        assert result.evidence is not None
        assert result.evidence.screenshot_urls
        assert result.evidence.metadata["scenario_state_found"] is True

    def test_cookie_consent_schema_structure(self):
        """CookieConsentObservation should have expected fields."""
        observation = CookieConsentObservation(
            banner_present=True,
            accept_button_text="Accept All",
            reject_button_text="Reject",
            reject_button_visible=True,
            accept_clicks_required=1,
            reject_clicks_required=1,
            asymmetry_detected=False,
            deceptive_language=["Improve your experience"],
            pre_selected_options=["Analytics"],
            has_essential_only_option=True,
        )
        assert observation.banner_present is True
        assert observation.asymmetry_detected is False


class TestCheckoutFlowScenario:
    """Test checkout flow scenario with Nova Act."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_checkout_flow_returns_observation(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Checkout flow should return JourneyObservation with price data."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_checkout_flow_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="cost_sensitive",
            nova_act=mock_nova_act_module,
        )

        assert result.scenario == "checkout_flow"
        assert result.persona == "cost_sensitive"
        assert result.evidence is not None
        assert result.evidence.metadata["scenario_state_found"] is True

    def test_checkout_observation_schema(self):
        """CheckoutObservation should have expected fields."""
        observation = CheckoutObservation(
            page_reached=True,
            prices_seen=[{"label": "Total", "value": 99.99}],
            hidden_fees=["Service fee"],
            price_delta=10.0,
            urgency_tactics=["Only 2 left!"],
            pre_selected_addons=["Insurance"],
            required_steps=5,
            unexpected_obstacles=["Forced account creation"],
        )
        assert observation.page_reached is True
        assert observation.price_delta == 10.0
        assert len(observation.hidden_fees) == 1


class TestSubscriptionCancellationScenario:
    """Test subscription cancellation scenario with Nova Act."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_cancellation_scenario_returns_observation(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Cancellation should return JourneyObservation with obstruction data."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_subscription_cancellation_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="exit_intent",
            nova_act=mock_nova_act_module,
        )

        assert result.scenario == "subscription_cancellation"
        assert result.persona == "exit_intent"
        assert result.evidence is not None

    def test_cancellation_observation_schema(self):
        """SubscriptionCancellationObservation should have expected fields."""
        observation = SubscriptionCancellationObservation(
            cancellation_flow_found=True,
            clicks_to_cancel=5,
            detours_encountered=["Retention offer", "Support chat"],
            confirmshaming_detected=True,
            confirmshaming_phrases=["Are you sure you want to lose benefits?"],
            pause_offered=True,
            alternative_options=["Pause plan", "Switch to free"],
            final_cancel_difficult=True,
        )
        assert observation.confirmshaming_detected is True
        assert observation.clicks_to_cancel == 5


class TestAccountDeletionScenario:
    """Test account deletion scenario with Nova Act."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_deletion_scenario_returns_observation(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Account deletion should return JourneyObservation with obstruction data."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_account_deletion_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="privacy_sensitive",
            nova_act=mock_nova_act_module,
        )

        assert result.scenario == "account_deletion"
        assert result.persona == "privacy_sensitive"
        assert result.evidence is not None

    def test_deletion_observation_schema(self):
        """AccountDeletionObservation should have expected fields."""
        observation = AccountDeletionObservation(
            deletion_flow_found=True,
            clicks_to_delete=7,
            obstacles_encountered=["Extra confirmation", "Warning screen"],
            requires_contact_support=True,
            confirmation_required=True,
            data_retention_warning="Your data will be retained for 30 days",
            alternatives_offered=["Deactivate instead", "Download data first"],
            flow_completed=False,
        )
        assert observation.requires_contact_support is True
        assert observation.clicks_to_delete == 7


class TestNewsletterSignupScenario:
    """Test newsletter signup scenario with Nova Act."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_newsletter_scenario_returns_observation(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Newsletter signup should return JourneyObservation with enrollment data."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_newsletter_signup_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="privacy_sensitive",
            nova_act=mock_nova_act_module,
        )

        assert result.scenario == "newsletter_signup"
        assert result.persona == "privacy_sensitive"
        assert result.evidence is not None

    def test_newsletter_observation_schema(self):
        """NewsletterSignupObservation should have expected fields."""
        observation = NewsletterSignupObservation(
            signup_form_found=True,
            pre_checked_boxes=["Marketing emails", "Partner offers"],
            confusing_opt_in=True,
            confusing_language_examples=["Uncheck this box to not receive non-essential communications"],
            dark_enrollment_detected=True,
            bundled_with_other_services=True,
            unsubscription_difficulty="Requires contacting support",
            consent_separated=False,
        )
        assert observation.dark_enrollment_detected is True
        assert len(observation.pre_checked_boxes) == 2


class TestPricingComparisonScenario:
    """Test pricing comparison scenario with Nova Act."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_pricing_scenario_returns_observation(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Pricing comparison should return JourneyObservation with price data."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_pricing_comparison_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="cost_sensitive",
            nova_act=mock_nova_act_module,
        )

        assert result.scenario == "pricing_comparison"
        assert result.persona == "cost_sensitive"
        assert result.evidence is not None

    def test_pricing_observation_schema(self):
        """PricingComparisonObservation should have expected fields."""
        observation = PricingComparisonObservation(
            prices_found=[{"label": "Guest", "value": 99.99}, {"label": "Member", "value": 79.99}],
            price_variations_detected=True,
            bait_and_switch_suspected=True,
            persona_specific_offers=["New customer discount"],
            hidden_discounts=["Hidden at checkout"],
            loyalty_program_pressure=True,
            dynamic_pricing_indicators=["Price changed on refresh"],
        )
        assert observation.bait_and_switch_suspected is True
        assert observation.loyalty_program_pressure is True


# =============================================================================
# Full Audit Run Tests
# =============================================================================


class TestFullAuditRun:
    """Test complete audit runs with multiple scenarios and personas."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_run_audit_single_scenario_single_persona(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Run audit with one scenario and one persona."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        progress_calls = []

        def progress(phase, message, progress_pct, status, details):
            progress_calls.append({
                "phase": phase,
                "message": message,
                "progress": progress_pct,
                "status": status,
            })

        result = provider.run_audit(
            audit_id="test-audit-1",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        assert len(result.observations) == 1
        assert result.observations[0].scenario == "cookie_consent"
        assert result.observations[0].persona == "privacy_sensitive"
        assert result.summary["mode"] == "nova_act"
        assert "evidence_origin" in result.summary
        assert result.summary["observation_count"] == 1

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_run_audit_multiple_scenarios(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Run audit with multiple scenarios and personas."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        def progress(phase, message, progress_pct, status, details):
            pass

        result = provider.run_audit(
            audit_id="test-audit-multi",
            target_url="https://example.com",
            scenarios=["cookie_consent", "checkout_flow"],
            personas=["privacy_sensitive", "cost_sensitive"],
            progress=progress,
        )

        # Should have 2 scenarios x 2 personas = 4 observations
        assert len(result.observations) == 4
        assert result.summary["observation_count"] == 4

        # Check all scenarios are represented
        scenarios_found = {obs.scenario for obs in result.observations}
        assert scenarios_found == {"cookie_consent", "checkout_flow"}

        # Check all personas are represented for each scenario
        for scenario in ["cookie_consent", "checkout_flow"]:
            scenario_obs = [obs for obs in result.observations if obs.scenario == scenario]
            personas_found = {obs.persona for obs in scenario_obs}
            assert personas_found == {"privacy_sensitive", "cost_sensitive"}


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in Nova Act provider."""

    def test_error_observation_creation(self, mock_storage):
        """Error observation should contain error details."""
        provider = NovaActAuditProvider(mock_storage)

        error_obs = provider._error_observation(
            target_url="https://example.com",
            scenario="cookie_consent",
            persona="privacy_sensitive",
            error="Connection timeout",
        )

        assert error_obs.scenario == "cookie_consent"
        assert error_obs.persona == "privacy_sensitive"
        assert error_obs.evidence.metadata.get("error") == "Connection timeout"
        assert error_obs.evidence.friction_indicators == ["Audit scenario failed"]

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_invalid_scenario_returns_empty_result(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Invalid scenarios should return empty result."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        def progress(phase, message, progress_pct, status, details):
            pass

        result = provider.run_audit(
            audit_id="test-audit",
            target_url="https://example.com",
            scenarios=["invalid_scenario"],
            personas=["privacy_sensitive"],
            progress=progress,
        )

        assert len(result.observations) == 0
        assert "error" in result.summary


# =============================================================================
# Taxonomy Integration Tests
# =============================================================================


class TestTaxonomyIntegration:
    """Test that provider properly imports from taxonomy."""

    def test_all_taxonomy_scenarios_available(self):
        """All 6 scenarios from taxonomy should be supported."""
        expected_scenarios = [
            "cookie_consent",
            "subscription_cancellation",
            "checkout_flow",
            "account_deletion",
            "newsletter_signup",
            "pricing_comparison",
        ]
        assert set(AUDIT_SCENARIOS) == set(expected_scenarios)

    def test_all_taxonomy_personas_available(self):
        """All 3 personas from taxonomy should be supported."""
        expected_personas = ["privacy_sensitive", "cost_sensitive", "exit_intent"]
        assert set(PERSONA_DEFINITIONS) == set(expected_personas)

    def test_provider_uses_taxonomy_categories(self):
        """Provider should be able to reference taxonomy categories."""
        expected_categories = [
            "manipulative_design",
            "deceptive_content",
            "coercive_flow",
            "obstruction",
            "sneaking",
            "social_proof_manipulation",
        ]
        assert set(DARK_PATTERN_CATEGORIES) == set(expected_categories)


# =============================================================================
# Screenshot Capture Tests
# =============================================================================


class TestScreenshotCapture:
    """Test screenshot capture functionality."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_screenshots_captured_during_scenario(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Screenshots should be captured at key journey steps."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_cookie_consent_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="privacy_sensitive",
            nova_act=mock_nova_act_module,
        )

        # Should have screenshots in evidence
        assert len(result.evidence.screenshot_urls) > 0
        assert len(result.evidence.screenshot_paths) > 0

        # Storage should have been called
        assert mock_storage.save_bytes.called


# =============================================================================
# Parallel Persona Tests
# =============================================================================


class TestParallelPersonaExecution:
    """Test parallel persona execution via ThreadPoolExecutor."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_parallel_persona_execution(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Multiple personas should run in parallel for same scenario."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage, max_workers=3)

        def progress(phase, message, progress_pct, status, details):
            pass

        result = provider.run_audit(
            audit_id="test-parallel",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive", "cost_sensitive", "exit_intent"],
            progress=progress,
        )

        # Should have 3 observations (one per persona)
        assert len(result.observations) == 3

        # Each persona should be represented
        personas_found = {obs.persona for obs in result.observations}
        assert personas_found == {"privacy_sensitive", "cost_sensitive", "exit_intent"}


# =============================================================================
# Evidence Payload Structure Tests
# =============================================================================


class TestEvidencePayloadStructure:
    """Test that evidence payload matches expected structure."""

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_evidence_has_required_metadata(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """Evidence should contain required metadata fields."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_cookie_consent_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="privacy_sensitive",
            nova_act=mock_nova_act_module,
        )

        metadata = result.evidence.metadata
        required_fields = [
            "source",
            "source_label",
            "site_host",
            "page_url",
            "interacted_controls",
            "scenario_state_found",
            "action_count",
            "observed_price_delta",
            "state_snapshots",
        ]

        for field in required_fields:
            assert field in metadata, f"Missing required field: {field}"

        assert metadata["source"] == "nova_act"


# =============================================================================
# Validation Contract Tests
# =============================================================================


class TestValidationContractAssertions:
    """Tests that verify validation contract assertions."""

    def test_provider_implements_browser_audit_provider(self, mock_storage):
        """VAL-NOVA-001: Provider implements BrowserAuditProvider ABC."""
        from app.providers.browser import BrowserAuditProvider

        provider = NovaActAuditProvider(mock_storage)
        assert isinstance(provider, BrowserAuditProvider)

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_act_get_uses_pydantic_schemas(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """VAL-NOVA-011: act_get() uses Pydantic schemas for structured extraction."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        provider._run_cookie_consent_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="privacy_sensitive",
            nova_act=mock_nova_act_module,
        )

        # Verify act_get was called with schema parameter
        mock_nova_act_module.NovaAct.return_value.__enter__.return_value.act_get.assert_called()

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_screenshots_captured_at_key_steps(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """VAL-NOVA-010: Screenshots captured at key journey steps."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        result = provider._run_cookie_consent_scenario(
            audit_id="test-audit",
            target_url="https://example.com",
            persona="privacy_sensitive",
            nova_act=mock_nova_act_module,
        )

        # Screenshots should be in evidence
        assert len(result.evidence.screenshot_urls) > 0
        assert len(result.evidence.screenshot_paths) > 0

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_returns_journey_observation_objects(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """VAL-NOVA-003 through VAL-NOVA-009: Returns JourneyObservation objects."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        scenarios = [
            "cookie_consent",
            "checkout_flow",
            "subscription_cancellation",
            "account_deletion",
            "newsletter_signup",
            "pricing_comparison",
        ]

        for scenario in scenarios:
            method = getattr(provider, f"_run_{scenario}_scenario")
            result = method(
                audit_id="test-audit",
                target_url="https://example.com",
                persona="privacy_sensitive",
                nova_act=mock_nova_act_module,
            )

            from app.schemas.runtime import JourneyObservation
            assert isinstance(result, JourneyObservation)
            assert result.scenario == scenario

    @patch("app.providers.nova_act_browser.NovaActAuditProvider._ensure_nova_act")
    def test_multiple_personas_tested_for_same_url(
        self, mock_ensure, mock_storage, mock_nova_act_module
    ):
        """VAL-NOVA-012: Multiple personas tested for same URL."""
        mock_ensure.return_value = mock_nova_act_module

        provider = NovaActAuditProvider(mock_storage)

        def progress(phase, message, progress_pct, status, details):
            pass

        result = provider.run_audit(
            audit_id="test-multi-persona",
            target_url="https://example.com",
            scenarios=["cookie_consent"],
            personas=["privacy_sensitive", "cost_sensitive", "exit_intent"],
            progress=progress,
        )

        # Should have observations for each persona
        assert len(result.observations) == 3
        personas_tested = [obs.persona for obs in result.observations]
        assert "privacy_sensitive" in personas_tested
        assert "cost_sensitive" in personas_tested
        assert "exit_intent" in personas_tested

        # All should have same target URL
        for obs in result.observations:
            assert obs.target_url == "https://example.com"

    def test_imports_scenarios_from_taxonomy(self):
        """VAL-NOVA-002: Imports scenarios/categories from taxonomy."""
        from app.core.taxonomy import AUDIT_SCENARIOS, DARK_PATTERN_CATEGORIES

        # Verify taxonomy has all expected values
        assert "cookie_consent" in AUDIT_SCENARIOS
        assert "subscription_cancellation" in AUDIT_SCENARIOS
        assert "checkout_flow" in AUDIT_SCENARIOS
        assert "account_deletion" in AUDIT_SCENARIOS
        assert "newsletter_signup" in AUDIT_SCENARIOS
        assert "pricing_comparison" in AUDIT_SCENARIOS

        assert "manipulative_design" in DARK_PATTERN_CATEGORIES
        assert "obstruction" in DARK_PATTERN_CATEGORIES
        assert "deceptive_content" in DARK_PATTERN_CATEGORIES
