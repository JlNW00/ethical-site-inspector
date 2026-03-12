from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ObservationEvidence:
    screenshot_urls: list[str] = field(default_factory=list)
    screenshot_paths: list[str] = field(default_factory=list)
    button_labels: list[str] = field(default_factory=list)
    checkbox_states: dict[str, bool] = field(default_factory=dict)
    price_points: list[dict[str, Any]] = field(default_factory=list)
    text_snippets: list[str] = field(default_factory=list)
    dom_excerpt: str = ""
    step_count: int = 0
    friction_indicators: list[str] = field(default_factory=list)
    activity_log: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class JourneyObservation:
    scenario: str
    persona: str
    target_url: str
    final_url: str
    evidence: ObservationEvidence


@dataclass(slots=True)
class RuleFindingDraft:
    scenario: str
    persona: str
    pattern_family: str
    severity: str
    title: str
    evidence_excerpt: str
    rule_reason: str
    trust_impact: float
    evidence_payload: dict[str, Any]


@dataclass(slots=True)
class ClassifiedFinding:
    explanation: str
    remediation: str
    confidence: float
    severity: str


@dataclass(slots=True)
class BrowserRunResult:
    observations: list[JourneyObservation]
    summary: dict[str, Any]
