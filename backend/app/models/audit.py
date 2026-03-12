from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    summary: Mapped[str | None] = mapped_column(Text)
    trust_score: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    selected_scenarios: Mapped[list[str]] = mapped_column(JSON, default=list)
    selected_personas: Mapped[list[str]] = mapped_column(JSON, default=list)
    report_path: Mapped[str | None] = mapped_column(String(2048))
    report_public_url: Mapped[str | None] = mapped_column(String(2048))
    raw_run: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    findings: Mapped[list["Finding"]] = relationship(
        back_populates="audit",
        cascade="all, delete-orphan",
        order_by="Finding.order_index",
    )
    events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="audit",
        cascade="all, delete-orphan",
        order_by="AuditEvent.id",
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario: Mapped[str] = mapped_column(String(50), nullable=False)
    persona: Mapped[str] = mapped_column(String(50), nullable=False)
    pattern_family: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    rule_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    trust_impact: Mapped[float] = mapped_column(Float, default=5.0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    audit: Mapped[Audit] = relationship(back_populates="findings")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    audit: Mapped[Audit] = relationship(back_populates="events")
