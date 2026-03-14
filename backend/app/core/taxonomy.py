"""
Taxonomy - Single source of truth for dark pattern categories, audit scenarios,
severity levels, persona definitions, and regulatory mappings.

All backend modules should import from this file rather than hardcoding values.
"""

from __future__ import annotations

from typing import Literal, cast

# =============================================================================
# Dark Pattern Categories
# =============================================================================

DARK_PATTERN_CATEGORIES = [
    "manipulative_design",
    "deceptive_content",
    "coercive_flow",
    "obstruction",
    "sneaking",
    "social_proof_manipulation",
]

DarkPatternCategory = Literal[
    "manipulative_design",
    "deceptive_content",
    "coercive_flow",
    "obstruction",
    "sneaking",
    "social_proof_manipulation",
]

# Legacy pattern families (for backward compatibility with rule engine)
# These map to the new category system
PatternFamily = Literal[
    "asymmetric_choice",
    "hidden_costs",
    "confirmshaming",
    "obstruction",
    "sneaking",
    "urgency",
]

# Mapping from legacy pattern families to new dark pattern categories
PATTERN_FAMILY_TO_CATEGORY: dict[str, DarkPatternCategory] = {
    "asymmetric_choice": "manipulative_design",
    "hidden_costs": "deceptive_content",
    "confirmshaming": "coercive_flow",
    "obstruction": "obstruction",
    "sneaking": "sneaking",
    "urgency": "social_proof_manipulation",
}

# =============================================================================
# Audit Scenarios
# =============================================================================

AUDIT_SCENARIOS = [
    "cookie_consent",
    "subscription_cancellation",
    "checkout_flow",
    "account_deletion",
    "newsletter_signup",
    "pricing_comparison",
]

ScenarioType = Literal[
    "cookie_consent",
    "subscription_cancellation",
    "checkout_flow",
    "account_deletion",
    "newsletter_signup",
    "pricing_comparison",
]

# Legacy scenario names (for backward compatibility)
LEGACY_SCENARIO_NAMES: dict[str, str] = {
    "cancellation_flow": "subscription_cancellation",
}

# =============================================================================
# Persona Definitions
# =============================================================================

PERSONA_DEFINITIONS = [
    "privacy_sensitive",
    "cost_sensitive",
    "exit_intent",
]

PersonaType = Literal[
    "privacy_sensitive",
    "cost_sensitive",
    "exit_intent",
]

# Persona descriptions for documentation and UI
PERSONA_DESCRIPTIONS: dict[PersonaType, str] = {
    "privacy_sensitive": "User focused on privacy protections, data minimization, and consent transparency",
    "cost_sensitive": "User focused on finding best prices, avoiding hidden fees, and cost transparency",
    "exit_intent": "User attempting to leave, cancel, or abandon a service/process",
}

# =============================================================================
# Severity Levels
# =============================================================================

SEVERITY_LEVELS = [
    "low",
    "medium",
    "high",
    "critical",
]

SeverityType = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

# Severity ranking for comparison (higher = more severe)
SEVERITY_RANK: dict[SeverityType, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# =============================================================================
# Audit Status
# =============================================================================

AUDIT_STATUSES = [
    "queued",
    "running",
    "completed",
    "failed",
]

AuditStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed",
]

# =============================================================================
# Regulatory Mappings
# =============================================================================

# Regulations that can be referenced
REGULATIONS = [
    "FTC",
    "GDPR",
    "DSA",
    "CPRA",
]

RegulationType = Literal[
    "FTC",
    "GDPR",
    "DSA",
    "CPRA",
]

# Regulation full names for display
REGULATION_FULL_NAMES: dict[RegulationType, str] = {
    "FTC": "Federal Trade Commission Act",
    "GDPR": "General Data Protection Regulation",
    "DSA": "Digital Services Act",
    "CPRA": "California Privacy Rights Act",
}

# Regulation citation data - specific articles, sections, and guidelines
REGULATION_CITATIONS: dict[RegulationType, list[dict[str, str]]] = {
    "FTC": [
        {
            "article": "FTC Act § 5",
            "title": "Unfair or Deceptive Acts or Practices",
            "description": "Prohibits unfair or deceptive acts or practices in or affecting commerce.",
        },
        {
            "article": "16 CFR Part 425",
            "title": "Trade Regulation Rule Concerning Negative Option Programs",
            "description": "Click-to-Cancel rule requiring simple cancellation mechanisms.",
        },
        {
            "article": "FTC Act § 12",
            "title": "False Advertisements",
            "description": "Prohibits dissemination of false advertisements for food, drugs, devices, or cosmetics.",
        },
        {
            "article": "Restore Online Shoppers' Confidence Act",
            "title": "ROSCA - Post-Transaction Third-Party Sellers",
            "description": "Requires clear disclosure of third-party sellers and express informed consent.",
        },
    ],
    "GDPR": [
        {
            "article": "Article 25",
            "title": "Data Protection by Design and by Default",
            "description": "Requires implementation of appropriate technical and organizational measures to ensure data protection principles are integrated into processing activities.",
        },
        {
            "article": "Article 5(1)(a)",
            "title": "Lawfulness, Fairness and Transparency",
            "description": "Personal data must be processed lawfully, fairly and in a transparent manner.",
        },
        {
            "article": "Article 7",
            "title": "Conditions for Consent",
            "description": "Consent must be freely given, specific, informed and unambiguous indication of data subject's wishes.",
        },
        {
            "article": "Article 8",
            "title": "Conditions Applicable to Child's Consent",
            "description": "Special protections for children in relation to information society services.",
        },
    ],
    "DSA": [
        {
            "article": "Article 25",
            "title": "Protection of Minors",
            "description": "Providers of online platforms shall take appropriate measures to ensure a high level of privacy, safety and security of minors.",
        },
        {
            "article": "Article 27",
            "title": "Dark Patterns Prohibition",
            "description": "Prohibits designing, organizing or operating online interfaces in a way that deceives or manipulates recipients of the service.",
        },
        {
            "article": "Article 26",
            "title": "Additional Obligations for Marketplaces",
            "description": "Transparency requirements for online marketplaces regarding traders and products.",
        },
        {
            "article": "Recital 67",
            "title": "Interface Design Transparency",
            "description": "Providers should not design their online interfaces in a way that deceives, manipulates, or materially distorts decision-making.",
        },
    ],
    "CPRA": [
        {
            "article": "Section 1798.185(a)(20)",
            "title": "Dark Patterns Prohibition",
            "description": "Prohibits using dark patterns to subvert or impair consumer choice regarding the sale or sharing of personal information.",
        },
        {
            "article": "Section 1798.100",
            "title": "Consumer Right to Know",
            "description": "Consumers have the right to know what personal information is being collected about them.",
        },
        {
            "article": "Section 1798.130",
            "title": "Notice at Collection",
            "description": "Businesses must provide notice at or before the point of collection about categories of personal information collected.",
        },
        {
            "article": "Section 1798.120",
            "title": "Right to Opt-Out of Sale/Sharing",
            "description": "Consumers have the right to opt-out of the sale or sharing of their personal information.",
        },
    ],
}

# Mapping from dark pattern categories to applicable regulations
REGULATORY_MAPPING: dict[DarkPatternCategory, list[RegulationType]] = {
    "manipulative_design": ["FTC", "DSA"],
    "deceptive_content": ["FTC", "GDPR", "DSA"],
    "coercive_flow": ["FTC", "DSA"],
    "obstruction": ["GDPR", "DSA", "CPRA"],
    "sneaking": ["FTC", "GDPR", "DSA", "CPRA"],
    "social_proof_manipulation": ["FTC", "DSA"],
}

# Alternative mapping from legacy pattern families to regulations
# (for backward compatibility during transition)
PATTERN_FAMILY_REGULATORY_MAPPING: dict[str, list[RegulationType]] = {
    "asymmetric_choice": ["FTC", "DSA"],
    "hidden_costs": ["FTC", "GDPR", "DSA"],
    "confirmshaming": ["FTC", "DSA"],
    "obstruction": ["GDPR", "DSA", "CPRA"],
    "sneaking": ["FTC", "GDPR", "DSA", "CPRA"],
    "urgency": ["FTC", "DSA"],
}

# =============================================================================
# Scenario to Category Mapping
# =============================================================================

# Which categories are most relevant to which scenarios
SCENARIO_RELEVANT_CATEGORIES: dict[ScenarioType, list[DarkPatternCategory]] = {
    "cookie_consent": ["manipulative_design", "obstruction", "sneaking"],
    "subscription_cancellation": ["obstruction", "coercive_flow", "manipulative_design"],
    "checkout_flow": ["deceptive_content", "sneaking", "social_proof_manipulation"],
    "account_deletion": ["obstruction", "coercive_flow"],
    "newsletter_signup": ["sneaking", "manipulative_design"],
    "pricing_comparison": ["deceptive_content", "social_proof_manipulation"],
}

# =============================================================================
# Evidence Types
# =============================================================================

EVIDENCE_TYPES = [
    "nova_ai",
    "heuristic",
    "mock",
    "rule_based",
]

EvidenceType = Literal[
    "nova_ai",
    "heuristic",
    "mock",
    "rule_based",
]

# Evidence type labels for UI display
EVIDENCE_TYPE_LABELS: dict[str, str] = {
    "nova_ai": "Nova AI evidence",
    "heuristic": "Heuristic detection",
    "mock": "Simulated",
    "rule_based": "Rule-based",
}

# =============================================================================
# Confidence Score Thresholds
# =============================================================================

# Confidence thresholds for evidence quality
CONFIDENCE_THRESHOLDS = {
    "nova_ai_high": 0.85,
    "nova_ai_medium": 0.75,
    "heuristic_high": 0.70,
    "heuristic_medium": 0.55,
    "minimum_viable": 0.40,
}

# Evidence type to confidence mapping (for initial confidence assignment)
EVIDENCE_TYPE_CONFIDENCE: dict[EvidenceType, float] = {
    "nova_ai": 0.80,
    "heuristic": 0.60,
    "rule_based": 0.65,
    "mock": 0.50,
}

# =============================================================================
# Helper Functions
# =============================================================================


def get_all_categories() -> list[str]:
    """Return all dark pattern category names."""
    return list(DARK_PATTERN_CATEGORIES)


def get_all_scenarios() -> list[str]:
    """Return all audit scenario names."""
    return list(AUDIT_SCENARIOS)


def get_all_personas() -> list[str]:
    """Return all persona names."""
    return list(PERSONA_DEFINITIONS)


def get_all_severity_levels() -> list[str]:
    """Return all severity level names."""
    return list(SEVERITY_LEVELS)


def get_regulations_for_category(category: str) -> list[str]:
    """Get applicable regulations for a given dark pattern category."""
    # Cast category to DarkPatternCategory if valid
    if category in DARK_PATTERN_CATEGORIES:
        result = REGULATORY_MAPPING.get(cast("DarkPatternCategory", category))
        if result:
            return list(result)
    return []


def get_regulations_for_pattern_family(pattern_family: str) -> list[str]:
    """Get applicable regulations for a legacy pattern family (backward compatibility)."""
    # Pattern families are legacy strings, not Literal types
    result = PATTERN_FAMILY_REGULATORY_MAPPING.get(pattern_family, [])
    if result:
        return list(result)
    return []


def category_to_pattern_family(category: str) -> str | None:
    """Map a dark pattern category to a legacy pattern family (if applicable)."""
    reverse_map: dict[str, str] = {v: k for k, v in PATTERN_FAMILY_TO_CATEGORY.items()}
    return reverse_map.get(category)


def pattern_family_to_category(pattern_family: str) -> DarkPatternCategory | None:
    """Map a legacy pattern family to a dark pattern category."""
    return PATTERN_FAMILY_TO_CATEGORY.get(pattern_family)


def is_valid_category(category: str) -> bool:
    """Check if a category name is valid."""
    return category in DARK_PATTERN_CATEGORIES


def is_valid_scenario(scenario: str) -> bool:
    """Check if a scenario name is valid."""
    return scenario in AUDIT_SCENARIOS


def is_valid_persona(persona: str) -> bool:
    """Check if a persona name is valid."""
    return persona in PERSONA_DEFINITIONS


def is_valid_severity(severity: str) -> bool:
    """Check if a severity level is valid."""
    return severity in SEVERITY_LEVELS


def compare_severity(severity1: SeverityType, severity2: SeverityType) -> int:
    """Compare two severity levels. Returns positive if severity1 > severity2."""
    return SEVERITY_RANK[severity1] - SEVERITY_RANK[severity2]


def get_relevant_categories_for_scenario(scenario: str) -> list[str]:
    """Get dark pattern categories relevant to a given scenario."""
    # Cast scenario to ScenarioType if valid
    if scenario in AUDIT_SCENARIOS:
        result = SCENARIO_RELEVANT_CATEGORIES.get(cast("ScenarioType", scenario))
        if result:
            return list(result)
    return []
