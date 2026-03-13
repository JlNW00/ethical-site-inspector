from __future__ import annotations

from sqlalchemy import select

from app.core.config import get_settings
from app.models import Audit
from app.schemas.audit import AuditCreateRequest
from app.services.audit_orchestrator import AuditOrchestrator


def ensure_seeded_demo(session_factory) -> str | None:
    settings = get_settings()
    with session_factory() as db:
        existing_id = db.scalar(
            select(Audit.id)
            .where(Audit.status == "completed", Audit.report_path.is_not(None))
            .order_by(Audit.created_at.desc())
            .limit(1)
        )
        if existing_id:
            return existing_id

        orchestrator = AuditOrchestrator(session_factory)
        payload = AuditCreateRequest(
            target_url="https://demo.ethicalsiteinspector.local",
            scenarios=["cookie_consent", "checkout_flow", "subscription_cancellation"],
            personas=["privacy_sensitive", "cost_sensitive", "exit_intent"],
        )
        audit = orchestrator.create_audit(
            db,
            payload,
            mode="mock" if settings.effective_mode != "live" else settings.effective_mode,
        )
        orchestrator.run_audit(audit.id, mode_override="mock")
        return audit.id
