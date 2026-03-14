r"""
Backfill regulatory data for existing findings.

This script:
1. Queries all findings from the database
2. Looks up their pattern_family in taxonomy.PATTERN_FAMILY_REGULATORY_MAPPING
3. Updates regulatory_categories, confidence, evidence_type in evidence_payload
4. Runs suppression logic to mark false positives
5. Inserts a fake failed audit for testing purposes (VAL-CROSS-005)

Usage:
    cd backend && .venv\Scripts\python.exe scripts/backfill_regulatory_data.py
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.core.taxonomy import (  # noqa: E402
    EVIDENCE_TYPE_CONFIDENCE,
    get_regulations_for_pattern_family,
)
from app.detectors.suppression import should_suppress
from app.models import Audit, AuditEvent, Finding


def backfill_regulatory_categories(session) -> int:
    """
    Backfill regulatory_categories for all findings based on their pattern_family.

    Returns the number of findings updated.
    """
    findings = session.query(Finding).all()
    updated_count = 0

    for finding in findings:
        # Get regulatory categories from pattern_family
        regulations = get_regulations_for_pattern_family(finding.pattern_family)

        # Update regulatory_categories if empty or not set
        if not finding.regulatory_categories or finding.regulatory_categories == []:
            finding.regulatory_categories = regulations
            updated_count += 1

    session.commit()
    print(f"Backfilled regulatory_categories for {updated_count} findings")
    return updated_count


def backfill_confidence_scores(session) -> int:
    """
    Backfill confidence scores based on evidence_type in evidence_payload.

    Nova AI evidence gets > 0.75, heuristic gets <= 0.75.

    Returns the number of findings updated.
    """
    findings = session.query(Finding).all()
    updated_count = 0

    for finding in findings:
        # Skip if confidence is already reasonably set (> 0.5 means it was likely set)
        if finding.confidence and finding.confidence > 0.5 and finding.confidence != 0.5:
            continue

        # Determine evidence type from payload
        evidence_payload = finding.evidence_payload or {}
        evidence_type = evidence_payload.get("evidence_type", "heuristic")

        # Set confidence based on evidence type
        if evidence_type == "nova_ai":
            finding.confidence = 0.80  # Nova AI > 0.75
        elif evidence_type == "rule_based":
            finding.confidence = 0.65  # Rule-based
        elif evidence_type == "heuristic":
            finding.confidence = 0.60  # Heuristic <= 0.75
        else:
            finding.confidence = EVIDENCE_TYPE_CONFIDENCE.get(evidence_type, 0.60)

        updated_count += 1

    session.commit()
    print(f"Backfilled confidence scores for {updated_count} findings")
    return updated_count


def backfill_evidence_type(session) -> int:
    """
    Ensure evidence_type is set in evidence_payload for all findings.

    Returns the number of findings updated.
    """
    findings = session.query(Finding).all()
    updated_count = 0

    for finding in findings:
        evidence_payload = finding.evidence_payload or {}

        # Check if evidence_type is missing
        if "evidence_type" not in evidence_payload:
            # Infer from confidence or default to heuristic
            if finding.confidence and finding.confidence > 0.75:
                evidence_payload["evidence_type"] = "nova_ai"
            elif finding.confidence and finding.confidence > 0.60:
                evidence_payload["evidence_type"] = "rule_based"
            else:
                evidence_payload["evidence_type"] = "heuristic"

            finding.evidence_payload = evidence_payload
            updated_count += 1

    session.commit()
    print(f"Backfilled evidence_type for {updated_count} findings")
    return updated_count


def run_suppression_logic(session) -> int:
    """
    Run suppression logic on all findings to mark false positives.

    Returns the number of findings suppressed.
    """
    findings = session.query(Finding).all()
    suppressed_count = 0

    for finding in findings:
        # Run suppression check
        is_suppressed = should_suppress(
            pattern_family=finding.pattern_family,
            evidence_payload=finding.evidence_payload or {},
            confidence=finding.confidence,
        )

        if is_suppressed and not finding.suppressed:
            finding.suppressed = True
            # Add suppression reason to evidence payload
            evidence_payload = finding.evidence_payload or {}
            evidence_payload["suppressed"] = True
            finding.evidence_payload = evidence_payload
            suppressed_count += 1

    session.commit()
    print(f"Suppressed {suppressed_count} findings as false positives")
    return suppressed_count


def insert_fake_failed_audit(session) -> str | None:
    """
    Insert a fake failed audit directly into the DB.

    This enables VAL-CROSS-005 testing (testing failure states).

    Returns the audit ID if created, None if a failed audit already exists.
    """
    # Check if there's already a failed audit
    existing_failed = session.query(Audit).filter(Audit.status == "failed").first()
    if existing_failed:
        print(f"Failed audit already exists: {existing_failed.id}")
        return existing_failed.id

    # Create fake failed audit
    audit_id = str(uuid.uuid4())
    now = datetime.now(datetime.UTC)

    audit = Audit(
        id=audit_id,
        target_url="https://example-failed-audit.com",
        mode="mock",
        status="failed",
        summary="Audit failed due to simulated error: Nova Act session timeout exceeded during cookie_consent scenario. The target site may have blocked automated access or the page structure changed unexpectedly.",
        trust_score=0.0,
        risk_level="unknown",
        selected_scenarios=["cookie_consent", "checkout_flow"],
        selected_personas=["privacy_sensitive"],
        raw_run={},
        metrics={"suppressed_count": 0, "error_phase": "cookie_consent", "error_type": "timeout"},
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=now,
    )

    session.add(audit)

    # Create terminal error event
    error_event = AuditEvent(
        audit_id=audit_id,
        phase="error",
        status="error",
        message="Audit failed: Nova Act session timeout exceeded during cookie_consent scenario. The target site may have blocked automated access or the page structure changed unexpectedly.",
        progress=100,
        details={
            "error_type": "timeout",
            "scenario": "cookie_consent",
            "persona": "privacy_sensitive",
            "terminal": True,
            "message": "Nova Act session timeout (120s) exceeded. Possible causes: site blocking, CAPTCHA, or page structure changed.",
        },
    )

    session.add(error_event)
    session.commit()

    print(f"Created fake failed audit: {audit_id}")
    return audit_id


def main():
    """Main entry point for the backfill script."""
    print("=" * 60)
    print("Backfill Regulatory Data Script")
    print("=" * 60)

    session = SessionLocal()

    try:
        # Get initial counts
        total_findings = session.query(Finding).count()
        total_audits = session.query(Audit).count()
        print(f"\nDatabase state:")
        print(f"  Total findings: {total_findings}")
        print(f"  Total audits: {total_audits}")

        # 1. Backfill regulatory categories
        print("\n[1/5] Backfilling regulatory categories...")
        regulatory_updated = backfill_regulatory_categories(session)

        # 2. Backfill confidence scores
        print("\n[2/5] Backfilling confidence scores...")
        confidence_updated = backfill_confidence_scores(session)

        # 3. Backfill evidence_type in payload
        print("\n[3/5] Backfilling evidence_type...")
        evidence_updated = backfill_evidence_type(session)

        # 4. Run suppression logic
        print("\n[4/5] Running suppression logic...")
        suppressed_count = run_suppression_logic(session)

        # 5. Insert fake failed audit
        print("\n[5/5] Inserting fake failed audit...")
        failed_audit_id = insert_fake_failed_audit(session)

        # Summary
        print("\n" + "=" * 60)
        print("Backfill Complete!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Regulatory categories updated: {regulatory_updated}")
        print(f"  - Confidence scores updated: {confidence_updated}")
        print(f"  - Evidence types updated: {evidence_updated}")
        print(f"  - Findings suppressed: {suppressed_count}")
        print(f"  - Failed audit ID: {failed_audit_id}")
        print(f"\nVerification:")
        print(f"  curl http://127.0.0.1:8000/api/audits/{failed_audit_id}/findings")
        print(f"  curl 'http://127.0.0.1:8000/api/audits?status=failed'")

    except Exception as e:
        print(f"\nError during backfill: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
