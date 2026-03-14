"""Tests for app.detectors.rule_engine – build_rule_findings()."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.detectors.rule_engine import build_rule_findings
from app.schemas.runtime import JourneyObservation, ObservationEvidence

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_observation(
    scenario: str = "cookie_consent",
    persona: str = "privacy_sensitive",
    *,
    button_labels: list[str] | None = None,
    checkbox_states: dict[str, bool] | None = None,
    price_points: list[dict] | None = None,
    text_snippets: list[str] | None = None,
    headings: list[str] | None = None,
    friction_indicators: list[str] | None = None,
    activity_log: list[str] | None = None,
    metadata: dict | None = None,
) -> JourneyObservation:
    meta = {"scenario_state_found": True}
    if metadata:
        meta.update(metadata)
    evidence = ObservationEvidence(
        button_labels=button_labels or [],
        checkbox_states=checkbox_states or {},
        price_points=price_points or [],
        text_snippets=text_snippets or [],
        headings=headings or [],
        friction_indicators=friction_indicators or [],
        activity_log=activity_log or [],
        metadata=meta,
    )
    return JourneyObservation(
        scenario=scenario,
        persona=persona,
        target_url="https://example.com",
        final_url="https://example.com/final",
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Asymmetric choice (cookie_consent)
# ---------------------------------------------------------------------------


class TestAsymmetricChoice:
    def test_accept_without_reject_triggers_asymmetric(self):
        obs = _make_observation(
            scenario="cookie_consent",
            button_labels=["Accept All", "Cookie Settings"],
        )
        findings = build_rule_findings(obs)
        families = [f.pattern_family for f in findings]
        assert "asymmetric_choice" in families

    def test_accept_with_reject_does_not_trigger_asymmetric(self):
        obs = _make_observation(
            scenario="cookie_consent",
            button_labels=["Accept All", "Reject All"],
        )
        findings = build_rule_findings(obs)
        families = [f.pattern_family for f in findings]
        assert "asymmetric_choice" not in families

    def test_asymmetric_severity_is_high(self):
        obs = _make_observation(
            scenario="cookie_consent",
            button_labels=["Accept All"],
        )
        findings = build_rule_findings(obs)
        asymmetric = [f for f in findings if f.pattern_family == "asymmetric_choice"]
        assert len(asymmetric) == 1
        assert asymmetric[0].severity == "high"


# ---------------------------------------------------------------------------
# Hidden costs (checkout_flow)
# ---------------------------------------------------------------------------


class TestHiddenCosts:
    def test_price_delta_triggers_hidden_costs(self):
        obs = _make_observation(
            scenario="checkout_flow",
            persona="cost_sensitive",
            price_points=[
                {"label": "Room rate", "value": 100.0, "state_label": "initial", "raw": "$100.00"},
                {"label": "Total", "value": 125.0, "state_label": "final", "raw": "$125.00"},
            ],
            metadata={
                "scenario_state_found": True,
                "observed_price_delta": 25.0,
            },
        )
        findings = build_rule_findings(obs)
        families = [f.pattern_family for f in findings]
        assert "hidden_costs" in families

    def test_critical_severity_for_large_delta(self):
        obs = _make_observation(
            scenario="checkout_flow",
            persona="cost_sensitive",
            price_points=[
                {"label": "Base", "value": 50.0, "state_label": "start", "raw": "$50.00"},
                {"label": "Total", "value": 70.0, "state_label": "end", "raw": "$70.00"},
            ],
            metadata={
                "scenario_state_found": True,
                "observed_price_delta": 20.0,
            },
        )
        findings = build_rule_findings(obs)
        hidden = [f for f in findings if f.pattern_family == "hidden_costs"]
        assert len(hidden) == 1
        assert hidden[0].severity == "critical"

    def test_high_severity_for_small_delta(self):
        obs = _make_observation(
            scenario="checkout_flow",
            persona="cost_sensitive",
            price_points=[
                {"label": "Base", "value": 50.0, "state_label": "start", "raw": "$50.00"},
                {"label": "Total", "value": 55.0, "state_label": "end", "raw": "$55.00"},
            ],
            metadata={
                "scenario_state_found": True,
                "observed_price_delta": 5.0,
            },
        )
        findings = build_rule_findings(obs)
        hidden = [f for f in findings if f.pattern_family == "hidden_costs"]
        assert len(hidden) == 1
        assert hidden[0].severity == "high"

    def test_no_hidden_costs_when_no_price_delta(self):
        obs = _make_observation(
            scenario="checkout_flow",
            persona="cost_sensitive",
            price_points=[
                {"label": "Total", "value": 50.0, "state_label": "start", "raw": "$50.00"},
                {"label": "Total", "value": 50.0, "state_label": "end", "raw": "$50.00"},
            ],
            metadata={
                "scenario_state_found": True,
                "observed_price_delta": 0.0,
            },
        )
        findings = build_rule_findings(obs)
        families = [f.pattern_family for f in findings]
        assert "hidden_costs" not in families


# ---------------------------------------------------------------------------
# Sneaking (pre-selected checkboxes in cookie_consent)
# ---------------------------------------------------------------------------


class TestSneaking:
    def test_preselected_checkboxes_trigger_sneaking(self):
        obs = _make_observation(
            scenario="cookie_consent",
            checkbox_states={
                "Analytics cookies": True,
                "Marketing cookies": True,
            },
        )
        findings = build_rule_findings(obs)
        families = [f.pattern_family for f in findings]
        assert "sneaking" in families

    def test_sneaking_severity_is_medium(self):
        obs = _make_observation(
            scenario="cookie_consent",
            checkbox_states={"Analytics cookies": True},
        )
        findings = build_rule_findings(obs)
        sneaking = [f for f in findings if f.pattern_family == "sneaking"]
        assert len(sneaking) == 1
        assert sneaking[0].severity == "medium"

    def test_no_sneaking_without_checked_boxes(self):
        obs = _make_observation(
            scenario="cookie_consent",
            checkbox_states={"Analytics cookies": False},
        )
        findings = build_rule_findings(obs)
        families = [f.pattern_family for f in findings]
        assert "sneaking" not in families


# ---------------------------------------------------------------------------
# Clean observation (no patterns detected)
# ---------------------------------------------------------------------------


class TestCleanObservation:
    def test_clean_cookie_consent_returns_empty(self):
        obs = _make_observation(
            scenario="cookie_consent",
            button_labels=["Accept", "Reject"],
            checkbox_states={"Analytics": False},
        )
        findings = build_rule_findings(obs)
        assert findings == []

    def test_scenario_state_not_found_returns_empty(self):
        obs = _make_observation(
            scenario="cookie_consent",
            button_labels=["Accept All"],
            metadata={"scenario_state_found": False},
        )
        findings = build_rule_findings(obs)
        assert findings == []

    def test_empty_evidence_returns_empty(self):
        obs = _make_observation(scenario="checkout_flow", persona="cost_sensitive")
        findings = build_rule_findings(obs)
        assert findings == []
