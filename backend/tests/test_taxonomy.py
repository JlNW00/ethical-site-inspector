"""
Tests for taxonomy module - verifies single source of truth for dark patterns.
"""

from __future__ import annotations

from app.core import taxonomy


class TestDarkPatternCategories:
    """Test dark pattern category definitions."""

    def test_all_six_categories_defined(self) -> None:
        """taxonomy has all 6 pattern categories."""
        expected_categories = [
            "manipulative_design",
            "deceptive_content",
            "coercive_flow",
            "obstruction",
            "sneaking",
            "social_proof_manipulation",
        ]
        assert sorted(taxonomy.DARK_PATTERN_CATEGORIES) == sorted(expected_categories)

    def test_get_all_categories_returns_list(self) -> None:
        """get_all_categories returns a list with all categories."""
        categories = taxonomy.get_all_categories()
        assert isinstance(categories, list)
        assert len(categories) == 6
        assert "manipulative_design" in categories
        assert "sneaking" in categories

    def test_is_valid_category_returns_true_for_valid(self) -> None:
        """is_valid_category returns True for valid categories."""
        assert taxonomy.is_valid_category("manipulative_design") is True
        assert taxonomy.is_valid_category("obstruction") is True

    def test_is_valid_category_returns_false_for_invalid(self) -> None:
        """is_valid_category returns False for invalid categories."""
        assert taxonomy.is_valid_category("invalid_category") is False
        assert taxonomy.is_valid_category("") is False


class TestAuditScenarios:
    """Test audit scenario definitions."""

    def test_all_six_scenarios_defined(self) -> None:
        """taxonomy has all 6 audit scenarios."""
        expected_scenarios = [
            "cookie_consent",
            "subscription_cancellation",
            "checkout_flow",
            "account_deletion",
            "newsletter_signup",
            "pricing_comparison",
        ]
        assert sorted(taxonomy.AUDIT_SCENARIOS) == sorted(expected_scenarios)

    def test_get_all_scenarios_returns_list(self) -> None:
        """get_all_scenarios returns a list with all scenarios."""
        scenarios = taxonomy.get_all_scenarios()
        assert isinstance(scenarios, list)
        assert len(scenarios) == 6
        assert "cookie_consent" in scenarios
        assert "pricing_comparison" in scenarios

    def test_is_valid_scenario_returns_true_for_valid(self) -> None:
        """is_valid_scenario returns True for valid scenarios."""
        assert taxonomy.is_valid_scenario("cookie_consent") is True
        assert taxonomy.is_valid_scenario("subscription_cancellation") is True

    def test_is_valid_scenario_returns_false_for_invalid(self) -> None:
        """is_valid_scenario returns False for invalid scenarios."""
        assert taxonomy.is_valid_scenario("invalid_scenario") is False
        assert taxonomy.is_valid_scenario("cancellation_flow") is False  # Legacy name


class TestPersonaDefinitions:
    """Test persona definitions."""

    def test_all_three_personas_defined(self) -> None:
        """taxonomy has all 3 persona definitions."""
        expected_personas = [
            "privacy_sensitive",
            "cost_sensitive",
            "exit_intent",
        ]
        assert sorted(taxonomy.PERSONA_DEFINITIONS) == sorted(expected_personas)

    def test_persona_descriptions_exist(self) -> None:
        """All personas have descriptions."""
        for persona in taxonomy.PERSONA_DEFINITIONS:
            assert persona in taxonomy.PERSONA_DESCRIPTIONS
            assert isinstance(taxonomy.PERSONA_DESCRIPTIONS[persona], str)
            assert len(taxonomy.PERSONA_DESCRIPTIONS[persona]) > 0

    def test_get_all_personas_returns_list(self) -> None:
        """get_all_personas returns a list with all personas."""
        personas = taxonomy.get_all_personas()
        assert isinstance(personas, list)
        assert len(personas) == 3
        assert "privacy_sensitive" in personas

    def test_is_valid_persona_returns_true_for_valid(self) -> None:
        """is_valid_persona returns True for valid personas."""
        assert taxonomy.is_valid_persona("privacy_sensitive") is True
        assert taxonomy.is_valid_persona("exit_intent") is True

    def test_is_valid_persona_returns_false_for_invalid(self) -> None:
        """is_valid_persona returns False for invalid personas."""
        assert taxonomy.is_valid_persona("invalid_persona") is False


class TestSeverityLevels:
    """Test severity level definitions."""

    def test_all_four_severity_levels_defined(self) -> None:
        """taxonomy has all 4 severity levels."""
        expected_severity = ["low", "medium", "high", "critical"]
        assert expected_severity == taxonomy.SEVERITY_LEVELS

    def test_severity_rank_order(self) -> None:
        """SEVERITY_RANK has correct ordering."""
        assert taxonomy.SEVERITY_RANK["low"] == 1
        assert taxonomy.SEVERITY_RANK["medium"] == 2
        assert taxonomy.SEVERITY_RANK["high"] == 3
        assert taxonomy.SEVERITY_RANK["critical"] == 4

    def test_get_all_severity_levels_returns_list(self) -> None:
        """get_all_severity_levels returns a list with all levels."""
        levels = taxonomy.get_all_severity_levels()
        assert isinstance(levels, list)
        assert len(levels) == 4
        assert "critical" in levels

    def test_is_valid_severity_returns_true_for_valid(self) -> None:
        """is_valid_severity returns True for valid severity."""
        assert taxonomy.is_valid_severity("low") is True
        assert taxonomy.is_valid_severity("critical") is True

    def test_compare_severity(self) -> None:
        """compare_severity correctly compares severity levels."""
        assert taxonomy.compare_severity("high", "low") > 0
        assert taxonomy.compare_severity("low", "high") < 0
        assert taxonomy.compare_severity("medium", "medium") == 0


class TestRegulatoryMappings:
    """Test regulatory mapping definitions."""

    def test_regulatory_mapping_has_all_categories(self) -> None:
        """REGULATORY_MAPPING includes all dark pattern categories."""
        for category in taxonomy.DARK_PATTERN_CATEGORIES:
            assert category in taxonomy.REGULATORY_MAPPING, f"{category} missing from regulatory mapping"

    def test_regulatory_mapping_returns_regulation_list(self) -> None:
        """get_regulations_for_category returns list of regulations."""
        regulations = taxonomy.get_regulations_for_category("sneaking")
        assert isinstance(regulations, list)
        assert "FTC" in regulations
        assert "GDPR" in regulations
        assert "DSA" in regulations
        assert "CPRA" in regulations

    def test_manipulative_design_maps_to_ftc_dsa(self) -> None:
        """manipulative_design maps to FTC and DSA."""
        regs = taxonomy.get_regulations_for_category("manipulative_design")
        assert "FTC" in regs
        assert "DSA" in regs

    def test_obstruction_maps_to_gdpr_dsa_cpra(self) -> None:
        """obstruction maps to GDPR, DSA, and CPRA."""
        regs = taxonomy.get_regulations_for_category("obstruction")
        assert "GDPR" in regs
        assert "DSA" in regs
        assert "CPRA" in regs

    def test_pattern_family_regulatory_mapping_backward_compat(self) -> None:
        """Pattern family regulatory mapping exists for backward compatibility."""
        assert "asymmetric_choice" in taxonomy.PATTERN_FAMILY_REGULATORY_MAPPING
        assert "hidden_costs" in taxonomy.PATTERN_FAMILY_REGULATORY_MAPPING


class TestScenarioCategoryMapping:
    """Test scenario to category relevance mapping."""

    def test_scenario_relevant_categories_exists(self) -> None:
        """SCENARIO_RELEVANT_CATEGORIES exists and has entries for all scenarios."""
        for scenario in taxonomy.AUDIT_SCENARIOS:
            assert scenario in taxonomy.SCENARIO_RELEVANT_CATEGORIES
            assert isinstance(taxonomy.SCENARIO_RELEVANT_CATEGORIES[scenario], list)
            assert len(taxonomy.SCENARIO_RELEVANT_CATEGORIES[scenario]) > 0

    def test_get_relevant_categories_for_scenario(self) -> None:
        """get_relevant_categories_for_scenario returns relevant categories."""
        cookie_categories = taxonomy.get_relevant_categories_for_scenario("cookie_consent")
        assert "manipulative_design" in cookie_categories
        assert "obstruction" in cookie_categories

        checkout_categories = taxonomy.get_relevant_categories_for_scenario("checkout_flow")
        assert "deceptive_content" in checkout_categories


class TestPatternFamilyCompatibility:
    """Test backward compatibility with legacy pattern families."""

    def test_pattern_family_to_category_mapping_exists(self) -> None:
        """PATTERN_FAMILY_TO_CATEGORY maps all legacy families."""
        expected_families = [
            "asymmetric_choice",
            "hidden_costs",
            "confirmshaming",
            "obstruction",
            "sneaking",
            "urgency",
        ]
        for family in expected_families:
            assert family in taxonomy.PATTERN_FAMILY_TO_CATEGORY
            assert taxonomy.PATTERN_FAMILY_TO_CATEGORY[family] in taxonomy.DARK_PATTERN_CATEGORIES

    def test_pattern_family_to_category_function(self) -> None:
        """pattern_family_to_category returns correct category."""
        assert taxonomy.pattern_family_to_category("hidden_costs") == "deceptive_content"
        assert taxonomy.pattern_family_to_category("confirmshaming") == "coercive_flow"

    def test_get_regulations_for_pattern_family_backward_compat(self) -> None:
        """get_regulations_for_pattern_family works for legacy families."""
        regs = taxonomy.get_regulations_for_pattern_family("hidden_costs")
        assert "FTC" in regs


class TestEvidenceTypes:
    """Test evidence type definitions."""

    def test_evidence_types_defined(self) -> None:
        """EVIDENCE_TYPES has all expected types."""
        expected = ["nova_ai", "heuristic", "mock", "rule_based"]
        assert expected == taxonomy.EVIDENCE_TYPES

    def test_evidence_type_labels_exist(self) -> None:
        """All evidence types have display labels."""
        for evidence_type in taxonomy.EVIDENCE_TYPES:
            assert evidence_type in taxonomy.EVIDENCE_TYPE_LABELS
            assert isinstance(taxonomy.EVIDENCE_TYPE_LABELS[evidence_type], str)

    def test_evidence_type_confidence_mapping(self) -> None:
        """EVIDENCE_TYPE_CONFIDENCE has entries for all types."""
        for evidence_type in taxonomy.EVIDENCE_TYPES:
            assert evidence_type in taxonomy.EVIDENCE_TYPE_CONFIDENCE
            assert 0 <= taxonomy.EVIDENCE_TYPE_CONFIDENCE[evidence_type] <= 1


class TestConfidenceThresholds:
    """Test confidence threshold definitions."""

    def test_confidence_thresholds_defined(self) -> None:
        """CONFIDENCE_THRESHOLDS has expected keys."""
        expected_keys = ["nova_ai_high", "nova_ai_medium", "heuristic_high", "heuristic_medium", "minimum_viable"]
        for key in expected_keys:
            assert key in taxonomy.CONFIDENCE_THRESHOLDS

    def test_confidence_thresholds_are_valid(self) -> None:
        """All confidence thresholds are between 0 and 1."""
        for key, value in taxonomy.CONFIDENCE_THRESHOLDS.items():
            assert 0 <= value <= 1, f"{key} has invalid value {value}"


class TestTypeExports:
    """Test that Literal types are properly exported."""

    def test_dark_pattern_category_type_exists(self) -> None:
        """DarkPatternCategory type exists and can be imported."""
        from app.core.taxonomy import DarkPatternCategory

        # Just verify it exists and is a type
        assert DarkPatternCategory is not None

    def test_scenario_type_exists(self) -> None:
        """ScenarioType type exists and can be imported."""
        from app.core.taxonomy import ScenarioType

        assert ScenarioType is not None

    def test_persona_type_exists(self) -> None:
        """PersonaType type exists and can be imported."""
        from app.core.taxonomy import PersonaType

        assert PersonaType is not None

    def test_severity_type_exists(self) -> None:
        """SeverityType type exists and can be imported."""
        from app.core.taxonomy import SeverityType

        assert SeverityType is not None

    def test_audit_status_type_exists(self) -> None:
        """AuditStatus type exists and can be imported."""
        from app.core.taxonomy import AuditStatus

        assert AuditStatus is not None


class TestNoHardcodedValues:
    """Test that taxonomy is used consistently - no hardcoding elsewhere."""

    def test_severity_rank_imported_from_taxonomy(self) -> None:
        """SEVERITY_RANK should be imported from taxonomy in rule_engine."""
        # This is verified by the import in rule_engine.py
        # The test ensures the value matches
        from app.detectors.rule_engine import SEVERITY_RANK as RuleEngineSeverityRank

        assert RuleEngineSeverityRank == taxonomy.SEVERITY_RANK
