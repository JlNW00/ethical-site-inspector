from __future__ import annotations

from collections import Counter

from app.schemas.runtime import JourneyObservation, RuleFindingDraft


def build_rule_findings(observation: JourneyObservation) -> list[RuleFindingDraft]:
    evidence = observation.evidence
    findings: list[RuleFindingDraft] = []
    text = " ".join(evidence.text_snippets).lower()
    friction_text = " | ".join(evidence.friction_indicators).lower()
    prices = [float(item["value"]) for item in evidence.price_points if isinstance(item.get("value"), (float, int))]
    price_delta = prices[-1] - prices[0] if len(prices) >= 2 else 0.0
    checked_boxes = [name for name, checked in evidence.checkbox_states.items() if checked]

    def add(pattern_family: str, severity: str, title: str, excerpt: str, rule_reason: str, trust_impact: float) -> None:
        findings.append(
            RuleFindingDraft(
                scenario=observation.scenario,
                persona=observation.persona,
                pattern_family=pattern_family,
                severity=severity,
                title=title,
                evidence_excerpt=excerpt,
                rule_reason=rule_reason,
                trust_impact=trust_impact,
                evidence_payload={
                    "screenshot_urls": evidence.screenshot_urls,
                    "screenshot_paths": evidence.screenshot_paths,
                    "button_labels": evidence.button_labels,
                    "checkbox_states": evidence.checkbox_states,
                    "price_points": evidence.price_points,
                    "friction_indicators": evidence.friction_indicators,
                    "activity_log": evidence.activity_log,
                    "dom_excerpt": evidence.dom_excerpt,
                },
            )
        )

    if observation.scenario == "cookie_consent":
        reject_visible = any("reject" in label.lower() or "essential" in label.lower() for label in evidence.button_labels)
        if not reject_visible and evidence.button_labels:
            add(
                "asymmetric_choice",
                "high",
                "Consent flow favors acceptance over refusal",
                evidence.button_labels[0],
                "Primary consent actions are more prominent than the refusal path.",
                10.0,
            )
        if checked_boxes:
            add(
                "sneaking",
                "medium",
                "Consent defaults include pre-selected options",
                ", ".join(checked_boxes),
                "Pre-checked consent or marketing toggles increase the chance of unintended acceptance.",
                8.0,
            )

    if price_delta > 0.01:
        add(
            "hidden_costs",
            "critical" if price_delta >= 10 else "high",
            "Price increases across the journey",
            f"Price changed by ${price_delta:.2f}",
            "Observed price points indicate extra fees or add-ons appear after initial commitment.",
            min(18.0, 8.0 + price_delta / 2),
        )

    if any(term in text for term in ["no thanks", "don't leave", "degraded experience", "stay on"]) or "guilting" in friction_text:
        add(
            "confirmshaming",
            "high",
            "Dismissal copy appears emotionally loaded",
            (evidence.text_snippets[0] if evidence.text_snippets else "Confirmshaming copy detected")[:220],
            "The flow uses emotionally loaded or guilt-inducing language to steer user choice.",
            11.0,
        )

    if evidence.step_count >= 5 or any(term in friction_text for term in ["support", "retention", "extra step"]):
        add(
            "obstruction",
            "critical" if evidence.step_count >= 7 else "high",
            "Journey requires excess effort to complete",
            f"{evidence.step_count} captured steps",
            "Measured friction exceeds a typical direct path and indicates obstruction.",
            12.0,
        )

    if any(term in text for term in ["only", "timer", "offer ends", "left at this price", "ending soon"]):
        add(
            "urgency",
            "medium",
            "Urgency messaging pressures immediate action",
            (evidence.text_snippets[0] if evidence.text_snippets else "Urgency signal detected")[:220],
            "Time or scarcity pressure may distort user decision-making.",
            7.0,
        )

    if checked_boxes or any(term in text for term in ["protection", "add-on", "bundle", "recommended option"]):
        add(
            "sneaking",
            "medium",
            "Additional option appears bundled into the journey",
            ", ".join(checked_boxes) if checked_boxes else "Bundled option copy detected",
            "Bundled extras or defaults can create unintentional opt-in behavior.",
            7.5,
        )

    if not findings and evidence.friction_indicators:
        dominant = Counter(evidence.friction_indicators).most_common(1)[0][0]
        add(
            "obstruction",
            "medium",
            "Friction indicators surfaced during the journey",
            dominant,
            "The audit captured friction signals even though rule matches were limited.",
            6.0,
        )

    return _dedupe(findings)


def _dedupe(findings: list[RuleFindingDraft]) -> list[RuleFindingDraft]:
    seen: set[tuple[str, str]] = set()
    result: list[RuleFindingDraft] = []
    for finding in findings:
        key = (finding.pattern_family, finding.title)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result
