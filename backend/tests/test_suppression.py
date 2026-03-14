"""
Tests for false-positive suppression rules and confidence scoring.

These tests verify that:
1. Low-confidence findings are suppressed
2. Legitimate cookie consent with equal options is not flagged as asymmetric
3. Legitimate inventory urgency is not flagged as deceptive
4. Nova AI evidence gets confidence > 0.75
5. Heuristic-only findings get confidence <= 0.75
"""

from __future__ import annotations

from app.core.taxonomy import (
    REGULATIONS,
)
from app.detectors.suppression import (
    apply_suppression,
    calculate_confidence,
    get_regulatory_categories,
    should_suppress,
)


class TestShouldSuppressLowConfidence:
    """Test suppression of low-confidence findings."""

    def test_suppresses_very_low_confidence(self):
        """Findings with confidence < 0.30 should be suppressed."""
        payload = {"scenario": "cookie_consent", "matched_buttons": ["Accept"]}
        assert should_suppress("asymmetric_choice", payload, confidence=0.25) is True
        assert should_suppress("hidden_costs", payload, confidence=0.29) is True

    def test_does_not_suppress_moderate_confidence(self):
        """Findings with confidence >= 0.30 should not be suppressed for low confidence alone."""
        payload = {"scenario": "cookie_consent", "matched_buttons": ["Accept"]}
        assert should_suppress("asymmetric_choice", payload, confidence=0.30) is False
        assert should_suppress("asymmetric_choice", payload, confidence=0.55) is False


class TestShouldSuppressCookieConsent:
    """Test suppression of legitimate cookie consent patterns."""

    def test_suppresses_legitimate_cookie_consent_with_equal_options(self):
        """
        Cookie consent with equal-weight accept/reject buttons is legitimate.
        Should be suppressed as false positive.
        """
        payload = {
            "scenario": "cookie_consent",
            "matched_buttons": ["Accept All", "Reject All", "Manage Preferences"],
            "detection_basis": "button contrast",
            "supporting_evidence": ["Accept All", "Reject All"],
        }
        assert should_suppress("asymmetric_choice", payload, confidence=0.60) is True

    def test_does_not_suppress_asymmetric_cookie_consent(self):
        """Cookie consent with only accept option should not be suppressed."""
        payload = {
            "scenario": "cookie_consent",
            "matched_buttons": ["Accept All", "Learn More"],
            "detection_basis": "button contrast",
            "supporting_evidence": ["Accept All"],
        }
        assert should_suppress("asymmetric_choice", payload, confidence=0.60) is False

    def test_does_not_suppress_non_cookie_consent_asymmetric(self):
        """Asymmetric choice in non-cookie contexts should not be suppressed."""
        payload = {
            "scenario": "checkout_flow",
            "matched_buttons": ["Subscribe", "No thanks (I hate saving money)"],
            "detection_basis": "button contrast",
        }
        assert should_suppress("asymmetric_choice", payload, confidence=0.70) is False


class TestShouldSuppressUrgency:
    """Test suppression of legitimate urgency patterns."""

    def test_suppresses_legitimate_inventory_urgency(self):
        """
        Legitimate inventory scarcity (rooms, seats) in checkout flow
        should be suppressed as false positive.
        """
        payload = {
            "scenario": "checkout_flow",
            "matched_quote": "Only 2 rooms available at this price",
        }
        assert should_suppress("urgency", payload, confidence=0.65) is True

    def test_suppresses_tickets_left_urgency(self):
        """Ticket inventory urgency should be suppressed."""
        payload = {
            "scenario": "checkout_flow",
            "matched_quote": "Only 5 tickets left!",
        }
        assert should_suppress("urgency", payload, confidence=0.65) is True

    def test_does_not_suppress_fake_urgency(self):
        """Generic urgency without inventory context should not be suppressed."""
        payload = {
            "scenario": "checkout_flow",
            "matched_quote": "Limited time offer ends soon!",
        }
        # Should not be suppressed (returns False unless other rules match)
        result = should_suppress("urgency", payload, confidence=0.65)
        # This returns False because there's no inventory term
        assert result is False

    def test_does_not_suppress_urgency_outside_checkout(self):
        """Urgency outside checkout flow should not be suppressed for inventory reasons."""
        payload = {
            "scenario": "cookie_consent",
            "matched_quote": "Only 2 rooms available",
        }
        # Not in checkout flow, so inventory urgency rule doesn't apply
        assert should_suppress("urgency", payload, confidence=0.65) is False


class TestShouldSuppressSneaking:
    """Test suppression of legitimate pre-checked security options."""

    def test_suppresses_essential_security_pre_checked(self):
        """
        Pre-checked security options (2FA, MFA) should be suppressed
        as they are legitimate account protection features.
        """
        payload = {
            "scenario": "account_deletion",
            "matched_buttons": ["Enable 2FA", "Security alerts"],
        }
        assert should_suppress("sneaking", payload, confidence=0.60) is True

    def test_suppresses_authentication_pre_checked(self):
        """Pre-checked authentication options should be suppressed."""
        payload = {
            "scenario": "checkout_flow",
            "matched_buttons": ["Enable MFA", "Password protection"],
        }
        assert should_suppress("sneaking", payload, confidence=0.60) is True

    def test_does_not_suppress_marketing_pre_checked(self):
        """Pre-checked marketing options should NOT be suppressed."""
        payload = {
            "scenario": "checkout_flow",
            "matched_buttons": ["Send me marketing emails", "Newsletter signup"],
        }
        assert should_suppress("sneaking", payload, confidence=0.60) is False

    def test_does_not_suppress_mixed_pre_checked(self):
        """Mixed security + marketing pre-checked should NOT be suppressed."""
        payload = {
            "scenario": "checkout_flow",
            "matched_buttons": ["Enable 2FA", "Send me offers"],
        }
        assert should_suppress("sneaking", payload, confidence=0.60) is False


class TestShouldSuppressHiddenCosts:
    """Test suppression of legitimate taxes and fees."""

    def test_suppresses_legitimate_tax_fees(self):
        """
        Price increases due to taxes and government fees should be suppressed
        when confidence is low (heuristic-only detection).
        """
        payload = {
            "scenario": "checkout_flow",
            "matched_prices": [
                {"label": "Sales Tax", "value": 8.50},
                {"label": "Government Fee", "value": 2.00},
            ],
        }
        # Low confidence (heuristic only) + legitimate fees = suppress
        assert should_suppress("hidden_costs", payload, confidence=0.65) is True

    def test_does_not_suppress_hidden_costs_high_confidence(self):
        """High-confidence findings should NOT be suppressed even with tax terms."""
        payload = {
            "scenario": "checkout_flow",
            "matched_prices": [
                {"label": "Sales Tax", "value": 8.50},
            ],
        }
        # High confidence should not be suppressed
        assert should_suppress("hidden_costs", payload, confidence=0.85) is False

    def test_does_not_suppress_sneaky_fees(self):
        """Sneaky service fees should NOT be suppressed."""
        payload = {
            "scenario": "checkout_flow",
            "matched_prices": [
                {"label": "Convenience fee", "value": 5.99},
                {"label": "Processing fee", "value": 3.99},
            ],
        }
        # These are not in the legitimate fee terms list
        assert should_suppress("hidden_costs", payload, confidence=0.70) is False


class TestApplySuppression:
    """Test the apply_suppression wrapper function."""

    def test_returns_suppressed_true_and_updates_payload(self):
        """apply_suppression should return True and add suppression metadata."""
        payload = {
            "scenario": "cookie_consent",
            "matched_buttons": ["Accept", "Reject"],
            "detection_basis": "button contrast",
            "supporting_evidence": ["Accept", "Reject"],
        }
        suppressed, updated_payload = apply_suppression("asymmetric_choice", payload, confidence=0.60)

        assert suppressed is True
        assert updated_payload["suppressed"] is True
        assert "suppression_reason" in updated_payload
        assert updated_payload["suppression_reason"] == "legitimate_cookie_consent_equal_options"

    def test_returns_suppressed_false_without_reason(self):
        """When not suppressed, payload should have suppressed=False and no reason."""
        payload = {
            "scenario": "checkout_flow",
            "matched_buttons": ["Accept All"],  # Only accept, no reject
        }
        suppressed, updated_payload = apply_suppression("asymmetric_choice", payload, confidence=0.70)

        assert suppressed is False
        assert updated_payload["suppressed"] is False
        assert "suppression_reason" not in updated_payload


class TestCalculateConfidence:
    """Test confidence score calculation."""

    def test_nova_ai_evidence_gets_high_confidence(self):
        """Nova AI evidence should get confidence > 0.75."""
        payload = {"screenshot_paths": ["/path/to/screenshot.png"]}
        confidence = calculate_confidence(
            evidence_type="nova_ai",
            has_ai_evidence=True,
            has_heuristic_evidence=False,
            pattern_family="asymmetric_choice",
            evidence_payload=payload,
        )
        assert confidence > 0.75
        assert confidence <= 1.0

    def test_nova_ai_with_heuristic_gets_very_high_confidence(self):
        """Nova AI + heuristic evidence should get very high confidence."""
        payload = {
            "screenshot_paths": ["/path/to/screenshot.png"],
            "matched_buttons": ["Accept", "Reject"],
        }
        confidence = calculate_confidence(
            evidence_type="nova_ai",
            has_ai_evidence=True,
            has_heuristic_evidence=True,
            pattern_family="hidden_costs",
            evidence_payload=payload,
        )
        assert confidence >= 0.85  # Should be at least nova_ai_high threshold

    def test_heuristic_only_gets_low_confidence(self):
        """Heuristic-only findings should get confidence <= 0.75."""
        payload = {"matched_buttons": ["Accept"]}
        confidence = calculate_confidence(
            evidence_type="heuristic",
            has_ai_evidence=False,
            has_heuristic_evidence=True,
            pattern_family="asymmetric_choice",
            evidence_payload=payload,
        )
        assert confidence <= 0.75

    def test_mock_evidence_gets_low_confidence(self):
        """Mock evidence should get low confidence."""
        payload = {}
        confidence = calculate_confidence(
            evidence_type="mock",
            has_ai_evidence=False,
            has_heuristic_evidence=False,
            pattern_family="urgency",
            evidence_payload=payload,
        )
        assert confidence <= 0.55  # Mock base confidence is 0.50

    def test_evidence_richness_increases_confidence(self):
        """Rich evidence should increase confidence."""
        # Rich payload with screenshots, buttons, quotes, activity log
        rich_payload = {
            "screenshot_paths": ["/path/screenshot.png"],
            "screenshot_urls": ["/url/screenshot.png"],
            "matched_buttons": ["Accept", "Reject"],
            "matched_quote": "Accept cookies to continue",
            "activity_log": ["Loaded page", "Found banner", "Clicked button"],
            "friction_indicators": ["Asymmetric choice"],
        }

        # Minimal payload
        minimal_payload = {}

        rich_confidence = calculate_confidence(
            evidence_type="heuristic",
            has_ai_evidence=False,
            has_heuristic_evidence=True,
            pattern_family="asymmetric_choice",
            evidence_payload=rich_payload,
        )

        minimal_confidence = calculate_confidence(
            evidence_type="heuristic",
            has_ai_evidence=False,
            has_heuristic_evidence=True,
            pattern_family="asymmetric_choice",
            evidence_payload=minimal_payload,
        )

        # Rich evidence should have higher confidence
        assert rich_confidence > minimal_confidence

    def test_confidence_never_exceeds_max(self):
        """Confidence should never exceed 0.98."""
        # Even with perfect evidence
        perfect_payload = {
            "screenshot_paths": ["/path/1.png", "/path/2.png"],
            "screenshot_urls": ["/url/1.png"],
            "matched_buttons": ["A", "B", "C"],
            "matched_quote": "Test quote",
            "activity_log": ["Step 1", "Step 2", "Step 3"],
            "friction_indicators": ["Friction 1", "Friction 2"],
        }
        confidence = calculate_confidence(
            evidence_type="nova_ai",
            has_ai_evidence=True,
            has_heuristic_evidence=True,
            pattern_family="hidden_costs",
            evidence_payload=perfect_payload,
        )
        assert confidence <= 0.98


class TestGetRegulatoryCategories:
    """Test regulatory category mapping from taxonomy."""

    def test_asymmetric_choice_maps_to_ftc_and_dsa(self):
        """asymmetric_choice should map to FTC and DSA."""
        categories = get_regulatory_categories("asymmetric_choice")
        assert "FTC" in categories
        assert "DSA" in categories
        assert "GDPR" not in categories

    def test_hidden_costs_maps_to_multiple_regulations(self):
        """hidden_costs should map to FTC, GDPR, and DSA."""
        categories = get_regulatory_categories("hidden_costs")
        assert "FTC" in categories
        assert "GDPR" in categories
        assert "DSA" in categories

    def test_obstruction_maps_to_gdpr_dsa_cpra(self):
        """obstruction should map to GDPR, DSA, and CPRA."""
        categories = get_regulatory_categories("obstruction")
        assert "GDPR" in categories
        assert "DSA" in categories
        assert "CPRA" in categories

    def test_sneaking_maps_to_all_regulations(self):
        """sneaking should map to all four regulations."""
        categories = get_regulatory_categories("sneaking")
        assert "FTC" in categories
        assert "GDPR" in categories
        assert "DSA" in categories
        assert "CPRA" in categories

    def test_unknown_pattern_family_returns_empty(self):
        """Unknown pattern families should return empty list."""
        categories = get_regulatory_categories("unknown_pattern")
        assert categories == []

    def test_all_pattern_families_have_regulations(self):
        """All defined pattern families should have at least one regulation."""
        pattern_families = ["asymmetric_choice", "hidden_costs", "confirmshaming", "obstruction", "sneaking", "urgency"]
        for family in pattern_families:
            categories = get_regulatory_categories(family)
            assert len(categories) > 0, f"Pattern family {family} should have regulations"
            # All categories should be valid regulations
            for cat in categories:
                assert cat in REGULATIONS


class TestIntegrationWithTaxonomy:
    """Test that suppression module properly integrates with taxonomy."""

    def test_uses_taxonomy_confidence_thresholds(self):
        """Should use confidence thresholds from taxonomy."""
        # Verify that the thresholds exist and are used
        from app.core.taxonomy import CONFIDENCE_THRESHOLDS

        assert "nova_ai_high" in CONFIDENCE_THRESHOLDS
        assert "nova_ai_medium" in CONFIDENCE_THRESHOLDS
        assert "heuristic_high" in CONFIDENCE_THRESHOLDS

        # Verify values (nova AI medium >= 0.75, heuristic <= 0.75)
        assert CONFIDENCE_THRESHOLDS["nova_ai_medium"] >= 0.75
        assert CONFIDENCE_THRESHOLDS["heuristic_high"] <= 0.75

    def test_uses_taxonomy_evidence_types(self):
        """Should use evidence types from taxonomy."""
        from app.core.taxonomy import EVIDENCE_TYPES

        assert "nova_ai" in EVIDENCE_TYPES
        assert "heuristic" in EVIDENCE_TYPES
        assert "mock" in EVIDENCE_TYPES
        assert "rule_based" in EVIDENCE_TYPES
