"""Benchmark model for multi-URL comparison audits."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class Benchmark(Base):
    """Benchmark model for comparing multiple URLs.

    A benchmark spawns individual audits per URL and aggregates their results.
    """

    __tablename__ = "benchmarks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    urls: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    audit_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    trust_scores: Mapped[dict[str, float] | None] = mapped_column(JSON, default=None, nullable=True)
    selected_scenarios: Mapped[list[str]] = mapped_column(JSON, default=list)
    selected_personas: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert benchmark to dictionary for serialization."""
        return {
            "id": self.id,
            "status": self.status,
            "urls": self.urls,
            "audit_ids": self.audit_ids,
            "trust_scores": self.trust_scores,
            "selected_scenarios": self.selected_scenarios,
            "selected_personas": self.selected_personas,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
