from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core.taxonomy import (
    PersonaType,
    ScenarioType,
)

# Local literal types for schema definitions
HealthStatus = Literal["ok"]
ReadinessStatus = Literal["ready"]


class AuditCreateRequest(BaseModel):
    target_url: HttpUrl
    scenarios: list[ScenarioType] = Field(default_factory=lambda: ["cookie_consent", "checkout_flow"])
    personas: list[PersonaType] = Field(default_factory=lambda: ["privacy_sensitive", "cost_sensitive"])


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phase: str
    status: str
    message: str
    progress: int
    details: dict[str, Any]
    created_at: datetime


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scenario: str
    persona: str
    pattern_family: str
    severity: str
    title: str
    explanation: str
    remediation: str
    evidence_excerpt: str
    rule_reason: str
    evidence_payload: dict[str, Any]
    confidence: float
    trust_impact: float
    order_index: int
    regulatory_categories: list[str] = []
    suppressed: bool = False
    created_at: datetime


class PersonaSummary(BaseModel):
    persona: str
    headline: str
    finding_count: int
    friction_index: int
    average_steps: float
    price_delta: float
    notable_patterns: list[str]


class ScenarioSummary(BaseModel):
    scenario: str
    headline: str
    risk_level: str
    finding_count: int
    dominant_patterns: list[str]


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_url: str
    mode: str
    status: str
    summary: str | None
    trust_score: float | None
    risk_level: str | None
    selected_scenarios: list[str]
    selected_personas: list[str]
    report_public_url: str | None
    metrics: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    events: list[AuditEventRead] = []


class FindingsResponse(BaseModel):
    audit_id: str
    findings: list[FindingRead]


class AuditListResponse(BaseModel):
    """Response schema for the list audits endpoint.

    Returns a list of AuditRead objects sorted by created_at descending.
    """

    audits: list[AuditRead]


class HealthResponse(BaseModel):
    status: HealthStatus
    timestamp: datetime
    version: str = "0.1.0"


class ReadinessResponse(BaseModel):
    status: ReadinessStatus
    configured_mode: str
    effective_mode: str
    browser_provider: str
    classifier_provider: str
    storage_provider: str
    nova_ready: bool
    playwright_ready: bool
    storage_ready: bool
    seeded_demo_audit_id: str | None


# Rebuild models to resolve forward references
AuditCreateRequest.model_rebuild()
AuditEventRead.model_rebuild()
FindingRead.model_rebuild()
PersonaSummary.model_rebuild()
ScenarioSummary.model_rebuild()
AuditRead.model_rebuild()
FindingsResponse.model_rebuild()
AuditListResponse.model_rebuild()
HealthResponse.model_rebuild()
ReadinessResponse.model_rebuild()
