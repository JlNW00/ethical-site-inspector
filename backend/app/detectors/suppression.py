"""
False-positive suppression rules for dark pattern findings.

This module identifies and marks findings as suppressed when they match
known false-positive patterns (e.g., cookie banners with equal-weight
accept/reject buttons are legitimate, not dark patterns).
"""

from __future__ import annotations

from typing import Any, cast

from app.core.taxonomy import get_regulations_for_pattern_family


def should_suppress(
    pattern_family: str,
    evidence_payload: dict[str, Any],
    confidence: float,
) -> bool:
    """
    Determine if a finding should be suppressed based on false-positive rules.

    Args:
        pattern_family: The pattern family of the finding
        evidence_payload: Evidence data containing detection details
        confidence: The confidence score of the finding

    Returns:
        True if the finding should be suppressed, False otherwise
    """
    # Rule 1: Suppress low-confidence findings below minimum threshold
    if confidence < 0.30:
        return True

    # Rule 2: Cookie consent with equal-weight accept/reject buttons is legitimate
    if pattern_family == "asymmetric_choice" and evidence_payload.get("scenario") == "cookie_consent":
        buttons = evidence_payload.get("matched_buttons", [])
        button_labels_lower = [b.lower() for b in buttons]

        has_accept = any(term in label for label in button_labels_lower for term in ("accept", "agree", "allow", "ok"))
        has_reject = any(
            term in label for label in button_labels_lower for term in ("reject", "decline", "refuse", "necessary")
        )

        # If both accept and reject options are present with similar prominence, it's not asymmetric
        if has_accept and has_reject:
            # Check for equal visual weight indicators (e.g., both are buttons not links)
            detection_basis = evidence_payload.get("detection_basis", "")
            if detection_basis == "button contrast":
                # If detection was based on button contrast but both options exist,
                # this is likely a false positive
                supporting = evidence_payload.get("supporting_evidence", [])
                # If we have explicit evidence of both accept and reject options
                if len(supporting) >= 2:
                    return True

    # Rule 3: Legitimate urgency for limited inventory (e.g., hotel rooms, event tickets)
    if pattern_family == "urgency":
        matched_quote = evidence_payload.get("matched_quote", "")
        quote_lower = matched_quote.lower()

        # These are legitimate scarcity indicators when verifiable
        legitimate_urgency_terms = [
            "rooms available",
            "seats remaining",
            "tickets left",
            "in stock",
            "inventory",
        ]
        if any(term in quote_lower for term in legitimate_urgency_terms):
            # Check if this is on a checkout flow (more likely legitimate)
            scenario = evidence_payload.get("scenario", "")
            if scenario == "checkout_flow":
                return True

    # Rule 4: Pre-checked boxes that are for legitimate account features (not marketing)
    if pattern_family == "sneaking":
        matched_buttons = evidence_payload.get("matched_buttons", [])
        # If all checked items are related to security or essential features
        essential_terms = ["security", "2fa", "mfa", "authentication", "verification", "protect"]
        marketing_terms = ["newsletter", "marketing", "promotional", "offers", "updates"]

        has_essential = any(term in btn.lower() for btn in matched_buttons for term in essential_terms)
        has_marketing = any(term in btn.lower() for btn in matched_buttons for term in marketing_terms)

        # If only essential features are pre-checked (no marketing), it's legitimate
        if has_essential and not has_marketing:
            return True

    # Rule 5: Hidden costs that are actually taxes or government fees (legitimate)
    if pattern_family == "hidden_costs":
        matched_prices = evidence_payload.get("matched_prices", [])
        price_labels = [str(p.get("label", "")).lower() for p in matched_prices]

        # Government fees and taxes are legitimate additions
        legitimate_fee_terms = [
            "tax",
            "vat",
            "gst",
            "sales tax",
            "government",
            "duty",
            "tariff",
            "shipping",
            "delivery",  # These are legitimate if disclosed
        ]

        # If the price increase is due to taxes/shipping, it may be legitimate
        # Check if all price changes are explained by legitimate fees
        all_legitimate = all(any(term in label for term in legitimate_fee_terms) for label in price_labels)
        if all_legitimate and len(price_labels) >= 2 and confidence <= 0.75:
            return True

    return False


def apply_suppression(
    pattern_family: str,
    evidence_payload: dict[str, Any],
    confidence: float,
) -> tuple[bool, dict[str, Any]]:
    """
    Apply suppression rules and update evidence_payload with suppression info.

    Args:
        pattern_family: The pattern family of the finding
        evidence_payload: Evidence data containing detection details
        confidence: The confidence score of the finding

    Returns:
        Tuple of (suppressed: bool, updated_payload: dict)
    """
    suppressed = should_suppress(pattern_family, evidence_payload, confidence)

    # Update evidence payload with suppression metadata
    updated_payload = evidence_payload.copy()
    updated_payload["suppressed"] = suppressed
    if suppressed:
        updated_payload["suppression_reason"] = _get_suppression_reason(pattern_family, evidence_payload, confidence)

    return suppressed, updated_payload


def _get_suppression_reason(
    pattern_family: str,
    evidence_payload: dict[str, Any],
    confidence: float,
) -> str:
    """Get the reason for suppression for logging/debugging purposes."""
    if confidence < 0.30:
        return "low_confidence"

    if pattern_family == "asymmetric_choice" and evidence_payload.get("scenario") == "cookie_consent":
        return "legitimate_cookie_consent_equal_options"

    if pattern_family == "urgency":
        return "legitimate_inventory_scarcity"

    if pattern_family == "sneaking":
        return "essential_security_features_pre_checked"

    if pattern_family == "hidden_costs":
        return "legitimate_taxes_fees_disclosed"

    return "false_positive_rule_match"


def calculate_confidence(
    evidence_type: str,
    has_ai_evidence: bool,
    has_heuristic_evidence: bool,
    pattern_family: str,
    evidence_payload: dict[str, Any],
) -> float:
    """
    Calculate confidence score based on evidence type and quality.

    Nova AI findings get confidence > 0.75, heuristic-only findings get <= 0.75.

    Args:
        evidence_type: Type of evidence (nova_ai, heuristic, rule_based, mock)
        has_ai_evidence: Whether Nova AI provided evidence
        has_heuristic_evidence: Whether heuristic detection found the pattern
        pattern_family: The pattern family detected
        evidence_payload: Full evidence payload for additional scoring

    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Base confidence from evidence type
    from app.core.taxonomy import (
        CONFIDENCE_THRESHOLDS,
        EVIDENCE_TYPE_CONFIDENCE,
        EVIDENCE_TYPES,
        EvidenceType,
    )

    base_confidence = (
        EVIDENCE_TYPE_CONFIDENCE.get(cast(EvidenceType, evidence_type), 0.50)
        if evidence_type in EVIDENCE_TYPES
        else 0.50
    )

    # Nova AI evidence gets high confidence
    if evidence_type == "nova_ai" or has_ai_evidence:
        # Nova AI findings always get confidence > 0.75
        if has_heuristic_evidence:
            # Both AI and heuristic: very high confidence
            confidence = max(base_confidence, CONFIDENCE_THRESHOLDS["nova_ai_high"])
        else:
            # AI only: high confidence
            confidence = max(base_confidence, CONFIDENCE_THRESHOLDS["nova_ai_medium"])
    elif evidence_type == "heuristic" or has_heuristic_evidence:
        # Heuristic-only findings get confidence <= 0.75
        confidence = min(base_confidence, CONFIDENCE_THRESHOLDS["heuristic_high"])
    else:
        # Default/rare case
        confidence = base_confidence

    # Adjust based on evidence richness
    evidence_richness = _calculate_evidence_richness(evidence_payload)
    confidence = min(0.98, confidence + (evidence_richness * 0.10))

    return round(confidence, 2)


def _calculate_evidence_richness(evidence_payload: dict[str, Any]) -> float:
    """
    Calculate how rich/detailed the evidence is (0.0 to 1.0).

    More detailed evidence = higher confidence adjustment.
    """
    richness = 0.0

    # Screenshots provide strong evidence
    if evidence_payload.get("screenshot_paths"):
        richness += 0.30
    if evidence_payload.get("screenshot_urls"):
        richness += 0.10

    # Specific matched elements
    if evidence_payload.get("matched_buttons"):
        richness += 0.15
    if evidence_payload.get("matched_quote"):
        richness += 0.15
    if evidence_payload.get("matched_prices"):
        richness += 0.10

    # Activity log shows audit trail
    if evidence_payload.get("activity_log"):
        richness += 0.10

    # Friction indicators
    if evidence_payload.get("friction_indicators"):
        richness += 0.10

    return min(1.0, richness)


def get_regulatory_categories(pattern_family: str) -> list[str]:
    """
    Get regulatory categories for a pattern family from taxonomy.

    Args:
        pattern_family: The pattern family to look up

    Returns:
        List of applicable regulation codes (e.g., ["FTC", "GDPR"])
    """
    return get_regulations_for_pattern_family(pattern_family)
