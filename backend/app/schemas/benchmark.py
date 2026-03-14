"""Pydantic schemas for Benchmark API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.core.taxonomy import AUDIT_SCENARIOS, PERSONA_DEFINITIONS


class BenchmarkCreate(BaseModel):
    """Request schema for creating a new benchmark.

    Requires 2-5 unique URLs to compare.
    """

    urls: list[HttpUrl] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="List of 2-5 URLs to compare",
    )
    selected_scenarios: list[str] = Field(
        ...,
        description="Scenarios to run for each URL",
    )
    selected_personas: list[str] = Field(
        ...,
        description="Personas to simulate for each URL",
    )

    @field_validator("urls", mode="after")
    @classmethod
    def validate_unique_urls(cls, v: list[HttpUrl]) -> list[HttpUrl]:
        """Ensure no duplicate URLs."""
        url_strs = [str(url) for url in v]
        if len(url_strs) != len(set(url_strs)):
            raise ValueError("Duplicate URLs are not allowed")
        return v

    @field_validator("selected_scenarios", mode="after")
    @classmethod
    def validate_scenarios(cls, v: list[str]) -> list[str]:
        """Ensure all scenarios are valid."""
        for scenario in v:
            if scenario not in AUDIT_SCENARIOS:
                raise ValueError(f"Invalid scenario: {scenario}. Must be one of: {AUDIT_SCENARIOS}")
        return v

    @field_validator("selected_personas", mode="after")
    @classmethod
    def validate_personas(cls, v: list[str]) -> list[str]:
        """Ensure all personas are valid."""
        for persona in v:
            if persona not in PERSONA_DEFINITIONS:
                raise ValueError(f"Invalid persona: {persona}. Must be one of: {PERSONA_DEFINITIONS}")
        return v


class BenchmarkRead(BaseModel):
    """Response schema for benchmark data.

    Includes all fields for displaying benchmark status and results.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    urls: list[str]
    audit_ids: list[str]
    trust_scores: dict[str, float] | None = None
    selected_scenarios: list[str]
    selected_personas: list[str]
    created_at: datetime
    updated_at: datetime


class BenchmarkListResponse(BaseModel):
    """Response schema for listing benchmarks."""

    benchmarks: list[BenchmarkRead]


# Rebuild models to resolve forward references
BenchmarkCreate.model_rebuild()
BenchmarkRead.model_rebuild()
BenchmarkListResponse.model_rebuild()
