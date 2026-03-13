from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.models import Audit, Finding
from app.schemas.audit import AuditCreateRequest, AuditRead, FindingsResponse
from app.services.audit_orchestrator import AuditOrchestrator
from app.services.pdf_service import generate_pdf_from_html



router = APIRouter(prefix="/audits", tags=["audits"])
orchestrator = AuditOrchestrator(SessionLocal)


@router.get("", response_model=list[AuditRead])
def list_audits(
    db: Session = Depends(get_db),
    status: Annotated[str | None, Query(description="Filter by audit status")] = None,
    url_contains: Annotated[str | None, Query(description="Case-insensitive URL search")] = None,
) -> list[Audit]:
    """List all audits with optional filtering.

    Returns an array of audits sorted by created_at descending.
    Supports optional query params:
    - status: Filter by status (completed, running, failed, queued)
    - url_contains: Case-insensitive search in target_url
    """
    # Build base query - select only columns we need (no events/findings for list)
    statement = select(Audit).order_by(desc(Audit.created_at))

    # Apply status filter if provided
    if status:
        statement = statement.where(Audit.status == status)

    # Apply URL contains filter if provided (case-insensitive)
    if url_contains:
        statement = statement.where(func.lower(Audit.target_url).contains(func.lower(url_contains)))

    audits = db.scalars(statement).all()
    return list(audits)


@router.post("", response_model=AuditRead, status_code=status.HTTP_202_ACCEPTED)
def create_audit(payload: AuditCreateRequest, db: Session = Depends(get_db)) -> Audit:
    settings = get_settings()
    audit = orchestrator.create_audit(db, payload, mode=settings.effective_mode)
    orchestrator.launch_audit(audit.id)
    return audit


@router.get("/{audit_id}", response_model=AuditRead)
def get_audit(audit_id: str, db: Session = Depends(get_db)) -> Audit:
    statement = select(Audit).where(Audit.id == audit_id).options(selectinload(Audit.events))
    audit = db.scalar(statement)
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


@router.get("/{audit_id}/findings", response_model=FindingsResponse)
def get_findings(audit_id: str, db: Session = Depends(get_db)) -> FindingsResponse:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id))
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    findings = list(db.scalars(select(Finding).where(Finding.audit_id == audit_id).order_by(Finding.order_index)).all())
    return FindingsResponse(audit_id=audit_id, findings=findings)


@router.get("/{audit_id}/report")
def get_report(audit_id: str, db: Session = Depends(get_db)) -> Response:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id))
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    if not audit.report_path:
        raise HTTPException(status_code=404, detail="Report not generated yet")

    report_path = Path(audit.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file missing")

    return FileResponse(
        report_path,
        media_type="text/html",
        filename=f"ethical-site-inspector-{audit.id}.html",
    )


@router.get("/{audit_id}/report/pdf")
def get_report_pdf(audit_id: str, db: Session = Depends(get_db)) -> Response:
    """Generate and download a PDF version of the audit report.

    Returns a PDF file containing:
    - Trust score
    - Risk level
    - Executive summary
    - Scenario breakdowns
    - Findings with severity

    Content-Type: application/pdf
    Content-Disposition: attachment with filename
    """
    audit = db.scalar(select(Audit).where(Audit.id == audit_id))
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    if not audit.report_path:
        raise HTTPException(status_code=404, detail="Report not generated yet")

    report_path = Path(audit.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file missing")

    try:
        html_content = report_path.read_text(encoding="utf-8")
        pdf_bytes = generate_pdf_from_html(html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    filename = f"ethical-site-inspector-{audit.id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
