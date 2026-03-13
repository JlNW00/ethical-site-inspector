from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import Audit
from app.schemas.audit import HealthResponse, ReadinessResponse
from app.services.provider_registry import (
    get_browser_provider,
    get_classifier_provider,
    get_storage_provider,
    is_playwright_ready,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=datetime.now(UTC))


@router.get("/readiness", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    settings = get_settings()
    browser_provider = get_browser_provider(settings.effective_mode, settings).__class__.__name__
    classifier_provider = get_classifier_provider(settings.effective_mode, settings).__class__.__name__
    storage_provider = get_storage_provider(settings).__class__.__name__
    with SessionLocal() as db:
        seeded_demo_audit_id = db.scalar(
            select(Audit.id)
            .where(Audit.status == "completed", Audit.report_path.is_not(None))
            .order_by(Audit.created_at.desc())
            .limit(1)
        )

    return ReadinessResponse(
        status="ready",
        configured_mode=settings.configured_mode,
        effective_mode=settings.effective_mode,
        browser_provider=browser_provider,
        classifier_provider=classifier_provider,
        storage_provider=storage_provider,
        nova_ready=settings.nova_ready,
        playwright_ready=is_playwright_ready(),
        storage_ready=True,
        seeded_demo_audit_id=seeded_demo_audit_id,
    )
