from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from app.core.taxonomy import SEVERITY_RANK, SeverityType
from app.schemas.runtime import JourneyObservation, RuleFindingDraft


def build_rule_findings(observation: JourneyObservation) -> list[RuleFindingDraft]:
    evidence = observation.evidence
    metadata = evidence.metadata
    if not metadata.get("scenario_state_found"):
        return []
    matched_findings: dict[str, RuleFindingDraft] = {}
    text_lines = [item for item in evidence.headings + evidence.text_snippets if item]
    checked_boxes = [name for name, checked in evidence.checkbox_states.items() if checked]
    prices = [item for item in evidence.price_points if isinstance(item.get("value"), float | int)]
    action_count = int(metadata.get("action_count", 0))
    _scenario_states = metadata.get("state_snapshots", [])

    def add_or_merge(
        pattern_family: str,
        severity: SeverityType,
        title: str,
        excerpt: str,
        rule_reason: str,
        trust_impact: float,
        *,
        matched_quote: str | None = None,
        matched_buttons: list[str] | None = None,
        matched_prices: list[dict[str, Any]] | None = None,
        supporting_evidence: list[str] | None = None,
        detection_basis: str | None = None,
    ) -> None:
        payload = _base_payload(observation)
        payload.update(
            {
                "matched_quote": matched_quote or excerpt,
                "matched_buttons": matched_buttons or [],
                "matched_prices": matched_prices or [],
                "supporting_evidence": supporting_evidence or [],
                "detection_basis": detection_basis or pattern_family,
            }
        )
        draft = RuleFindingDraft(
            scenario=observation.scenario,
            persona=observation.persona,
            pattern_family=pattern_family,
            severity=severity,
            title=title,
            evidence_excerpt=excerpt,
            rule_reason=rule_reason,
            trust_impact=trust_impact,
            evidence_payload=payload,
        )
        existing = matched_findings.get(pattern_family)
        if not existing:
            matched_findings[pattern_family] = draft
            return

        if SEVERITY_RANK.get(cast("SeverityType", draft.severity), 1) > SEVERITY_RANK.get(
            cast("SeverityType", existing.severity), 1
        ):
            existing.severity = draft.severity
        if len(draft.evidence_excerpt) > len(existing.evidence_excerpt):
            existing.evidence_excerpt = draft.evidence_excerpt
        if len(draft.rule_reason) > len(existing.rule_reason):
            existing.rule_reason = draft.rule_reason
        if len(draft.title) > len(existing.title):
            existing.title = draft.title
        existing.trust_impact = max(existing.trust_impact, draft.trust_impact)
        existing.evidence_payload["supporting_evidence"] = _merge_unique(
            existing.evidence_payload.get("supporting_evidence", []),
            payload.get("supporting_evidence", []),
            limit=6,
        )
        existing.evidence_payload["matched_buttons"] = _merge_unique(
            existing.evidence_payload.get("matched_buttons", []),
            payload.get("matched_buttons", []),
            limit=6,
        )
        existing.evidence_payload["matched_prices"] = _merge_price_points(
            existing.evidence_payload.get("matched_prices", []),
            payload.get("matched_prices", []),
            limit=4,
        )
        if payload.get("matched_quote") and payload.get("matched_quote") != existing.evidence_payload.get(
            "matched_quote"
        ):
            existing.evidence_payload["supporting_evidence"] = _merge_unique(
                existing.evidence_payload.get("supporting_evidence", []),
                [payload["matched_quote"]],
                limit=6,
            )

    if observation.scenario == "cookie_consent":
        accept_buttons = _matching_buttons(evidence.button_labels, ("accept", "agree", "allow", "ok", "continue"))
        explicit_reject_buttons = _matching_buttons(
            evidence.button_labels,
            ("reject", "decline", "refuse", "necessary only", "essential only", "continue without"),
        )
        alternate_buttons = _matching_buttons(
            evidence.button_labels, ("settings", "preferences", "manage", "learn more")
        )
        if accept_buttons and not explicit_reject_buttons:
            evidence_line = (
                f"Visible controls included {_format_list(accept_buttons)}"
                + (f" plus {_format_list(alternate_buttons)}." if alternate_buttons else ".")
                + " No equally explicit reject or decline action was captured in the same control set."
            )
            add_or_merge(
                "asymmetric_choice",
                "high",
                "Consent controls surface acceptance more clearly than refusal",
                evidence_line,
                "The captured consent state showed approval-oriented controls without an equally explicit refusal action in the same view.",
                10.0,
                matched_buttons=accept_buttons + alternate_buttons,
                supporting_evidence=accept_buttons + alternate_buttons,
                detection_basis="button contrast",
            )
        if checked_boxes:
            add_or_merge(
                "sneaking",
                "medium",
                "Consent settings include pre-selected choices",
                f"Checked controls observed: {_format_list(checked_boxes)}.",
                "The capture showed optional settings already selected before the user confirmed their choice.",
                8.0,
                matched_buttons=checked_boxes,
                supporting_evidence=checked_boxes,
                detection_basis="preselected checkbox",
            )

    price_delta = float(metadata.get("observed_price_delta", 0.0) or 0.0)
    distinct_price_states = {item.get("state_label") for item in prices if item.get("state_label")}
    if observation.scenario == "checkout_flow" and price_delta > 0.01 and len(distinct_price_states) >= 2:
        first_price = prices[0]
        last_price = prices[-1]
        first_raw = first_price.get("raw", "${:.2f}".format(first_price.get("value", 0)))
        last_raw = last_price.get("raw", "${:.2f}".format(last_price.get("value", 0)))
        first_label = str(first_price.get("label", ""))[:110]
        last_label = str(last_price.get("label", ""))[:110]
        first_state = first_price.get("state_label", "state 1")
        last_state = last_price.get("state_label", "state 2")
        price_excerpt = (
            f'{first_raw} in "{first_label}" '
            f"({first_state}) changed to {last_raw} "
            f'in "{last_label}" ({last_state}) '
            f"({price_delta:+.2f})."
        )
        add_or_merge(
            "hidden_costs",
            "critical" if price_delta >= 10 else "high",
            "Observed price moved during the audited journey",
            price_excerpt,
            "The run captured a visible price increase between two states of the same journey, which is a concrete hidden-cost risk signal.",
            min(18.0, 8.0 + price_delta / 2),
            matched_prices=[first_price, last_price],
            supporting_evidence=[str(first_price.get("label", "")), str(last_price.get("label", ""))],
            detection_basis="price delta",
        )

    confirm_quote = _first_matching_line(
        text_lines,
        ("lose my", "miss out", "before you go", "keep my", "stay enrolled", "stay on", "continue without"),
    )
    if confirm_quote and (
        observation.scenario != "cookie_consent"
        or any(
            term in confirm_quote.lower() for term in ("cookie", "consent", "privacy", "tracking", "accept", "reject")
        )
    ):
        add_or_merge(
            "confirmshaming",
            "high",
            "Observed decline copy applies pressure to the user",
            _quote(confirm_quote),
            f'The run captured emotionally loaded decline language: "{_quote(confirm_quote, limit=120)}".',
            11.0,
            matched_quote=confirm_quote,
            supporting_evidence=[confirm_quote],
            detection_basis="captured copy",
        )

    if action_count >= 2 or (
        observation.scenario == "subscription_cancellation"
        and action_count >= 1
        and any(
            "support" in item.lower() or "pause" in item.lower() for item in metadata.get("interacted_controls", [])
        )
    ):
        friction_summary = ", ".join(evidence.friction_indicators[:2])
        activity_summary = (
            "; ".join(evidence.activity_log[1:5])
            if len(evidence.activity_log) > 1
            else "No extra interactions were captured."
        )
        interacted_controls = metadata.get("interacted_controls", [])[:3]
        control_summary = " -> ".join(f'"{item[:60]}"' for item in interacted_controls)
        obstruction_excerpt = (
            f"{action_count} scenario interaction"
            + ("s were captured" if action_count != 1 else " was captured")
            + (f": {control_summary}." if control_summary else ".")
        )
        if friction_summary:
            obstruction_excerpt += f" Friction signals: {friction_summary}."
        add_or_merge(
            "obstruction",
            "critical" if action_count >= 4 else "high" if action_count >= 3 else "medium",
            "Observed path adds friction before the intended action",
            obstruction_excerpt,
            f"The audit path required {action_count} scenario-specific interactions. Activity included: {activity_summary}.",
            12.0 if action_count >= 3 else 6.5,
            supporting_evidence=evidence.activity_log[:4] + evidence.friction_indicators[:2],
            detection_basis="step count",
        )

    urgency_quote = _first_matching_line(
        text_lines, ("only", "left", "limited time", "offer ends", "deal ends", "last chance")
    )
    if (
        urgency_quote
        and observation.scenario in {"checkout_flow", "subscription_cancellation"}
        and _quote_is_scenario_grounded(observation.scenario, urgency_quote)
    ):
        add_or_merge(
            "urgency",
            "medium",
            "Observed scarcity or timing pressure in the UI",
            _quote(urgency_quote),
            f'The audit captured pressure-oriented copy: "{_quote(urgency_quote, limit=120)}".',
            7.0,
            matched_quote=urgency_quote,
            supporting_evidence=[urgency_quote],
            detection_basis="captured copy",
        )

    bundled_quote = _first_matching_line(
        text_lines, ("protection", "bundle", "save details", "recommended", "newsletter")
    )
    relevant_checked_boxes = checked_boxes
    relevant_bundled_quote = bundled_quote
    if observation.scenario == "checkout_flow":
        relevant_checked_boxes = [
            item
            for item in checked_boxes
            if any(
                term in item.lower()
                for term in ("save", "bundle", "protect", "insurance", "newsletter", "faster", "payment", "details")
            )
        ]
        if relevant_bundled_quote and not any(
            term in relevant_bundled_quote.lower()
            for term in ("protection", "bundle", "save details", "recommended", "newsletter")
        ):
            relevant_bundled_quote = None

    if observation.scenario in {"cookie_consent", "checkout_flow"} and (
        relevant_checked_boxes or relevant_bundled_quote
    ):
        excerpt = (
            f"Checked controls observed: {_format_list(relevant_checked_boxes)}."
            if relevant_checked_boxes
            else _quote(relevant_bundled_quote or "Bundled option copy detected")
        )
        support = relevant_checked_boxes[:] if relevant_checked_boxes else []
        if relevant_bundled_quote:
            support.append(relevant_bundled_quote)
        add_or_merge(
            "sneaking",
            "medium",
            "Optional choices appear bundled into the journey",
            excerpt,
            "The capture showed optional controls or bundled add-on language that could steer the user into unintended acceptance.",
            7.5,
            matched_quote=relevant_bundled_quote,
            matched_buttons=relevant_checked_boxes,
            supporting_evidence=support,
            detection_basis="bundled option",
        )

    return list(matched_findings.values())


def _base_payload(observation: JourneyObservation) -> dict[str, Any]:
    evidence = observation.evidence
    metadata = deepcopy(evidence.metadata)
    metadata.setdefault("source", "mock")
    metadata.setdefault("source_label", "Simulated")
    metadata.setdefault("site_host", observation.final_url)
    metadata.setdefault("page_url", observation.final_url)
    return {
        "source": metadata.get("source"),
        "source_label": metadata.get("source_label"),
        "site_host": metadata.get("site_host"),
        "page_title": evidence.page_title,
        "page_url": metadata.get("page_url", observation.final_url),
        "final_url": observation.final_url,
        "scenario": observation.scenario,
        "persona": observation.persona,
        "button_labels": evidence.button_labels,
        "checkbox_states": evidence.checkbox_states,
        "price_points": evidence.price_points,
        "text_snippets": evidence.text_snippets,
        "headings": evidence.headings,
        "friction_indicators": evidence.friction_indicators,
        "activity_log": evidence.activity_log,
        "dom_excerpt": evidence.dom_excerpt,
        "step_count": evidence.step_count,
        "screenshot_urls": evidence.screenshot_urls,
        "screenshot_paths": evidence.screenshot_paths,
        "interacted_controls": metadata.get("interacted_controls", []),
    }


def _matching_buttons(buttons: list[str], keywords: tuple[str, ...]) -> list[str]:
    """Find buttons that match any of the given keywords."""
    return [button for button in buttons if any(keyword in button.lower() for keyword in keywords)]


def _first_matching_line(lines: list[str], keywords: tuple[str, ...]) -> str | None:
    """Find first line matching any keyword."""
    for line in lines:
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in keywords):
            return line
    return None


def _price_delta(prices: list[dict[str, Any]]) -> float:
    """Calculate price delta between last and first prices."""
    if len(prices) < 2:
        return 0.0
    return float(prices[-1]["value"]) - float(prices[0]["value"])


def _quote_is_scenario_grounded(scenario: str, quote: str) -> bool:
    lower_quote = quote.lower()
    if scenario == "checkout_flow":
        return any(
            term in lower_quote
            for term in ("price", "night", "deal", "offer", "reserve", "availability", "room", "book")
        )
    if scenario == "subscription_cancellation":
        return any(term in lower_quote for term in ("cancel", "leave", "stay", "pause", "subscription"))
    return any(term in lower_quote for term in ("cookie", "consent", "privacy", "tracking"))


def _format_list(values: list[str], limit: int = 3) -> str:
    selected = [f'"{value}"' for value in values[:limit]]
    return ", ".join(selected)


def _quote(value: str, limit: int = 220) -> str:
    trimmed = " ".join(value.split()).strip()
    return trimmed[:limit]


def _merge_unique(first: list[str], second: list[str], limit: int = 6) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in first + second:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _merge_price_points(
    first: list[dict[str, Any]], second: list[dict[str, Any]], limit: int = 4
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for item in first + second:
        key = (str(item.get("label", "")), float(item.get("value", 0)))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result
