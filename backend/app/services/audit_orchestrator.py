from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timezone
from threading import Thread
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.detectors.rule_engine import build_rule_findings
from app.models import Audit, AuditEvent, Finding
from app.schemas.audit import AuditCreateRequest
from app.schemas.runtime import RuleFindingDraft
from app.services.provider_registry import (
    get_browser_provider,
    get_classifier_provider,
    get_fallback_browser_provider,
    get_storage_provider,
)
from app.services.report_service import ReportService


class AuditOrchestrator:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def create_audit(self, db: Session, payload: AuditCreateRequest, mode: str) -> Audit:
        audit = Audit(
            target_url=str(payload.target_url),
            mode=mode,
            status="queued",
            selected_scenarios=list(payload.scenarios),
            selected_personas=list(payload.personas),
        )
        db.add(audit)
        db.flush()
        db.add(
            AuditEvent(
                audit_id=audit.id,
                phase="queue",
                status="info",
                message="Audit queued and ready to run.",
                progress=2,
                details={"mode": mode},
            )
        )
        db.commit()
        return self.get_audit(db, audit.id)

    def launch_audit(self, audit_id: str, mode_override: str | None = None) -> None:
        Thread(target=self.run_audit, args=(audit_id, mode_override), daemon=True).start()

    def run_audit(self, audit_id: str, mode_override: str | None = None) -> None:
        """Run the full audit lifecycle with terminal failure handling.

        The entire run_audit method is wrapped in a top-level try/except to ensure
        that failed audits always reach a terminal state (status='failed') with
        proper error events and summaries, never getting stuck in 'running' state.
        """
        try:
            self._run_audit_internal(audit_id, mode_override)
        except Exception as exc:
            # Terminal failure handling: ensure audit reaches failed state
            self._handle_audit_failure(audit_id, exc)

    def _handle_audit_failure(self, audit_id: str, exc: Exception) -> None:
        """Handle terminal audit failure: set status='failed', emit error event, persist error summary."""
        error_message = f"Audit failed with unhandled exception: {exc.__class__.__name__}: {exc!s}"
        error_summary = f"The audit could not complete due to an error: {exc.__class__.__name__}. {str(exc)[:200]}"

        try:
            with self.session_factory() as db:
                audit = self.get_audit(db, audit_id)
                audit.status = "failed"
                audit.completed_at = datetime.now(UTC)
                audit.summary = error_summary

                # Emit terminal error event
                db.add(
                    AuditEvent(
                        audit_id=audit.id,
                        phase="error",
                        status="error",
                        message=error_message,
                        progress=100,
                        details={
                            "error_type": exc.__class__.__name__,
                            "error_message": str(exc)[:500],
                            "audit_id": audit_id,
                        },
                    )
                )
                db.commit()
        except Exception as inner_exc:
            # Last resort: if we can't even update the database, log the error
            import logging

            logger = logging.getLogger(__name__)
            logger.critical(f"Failed to update audit {audit_id} status to failed: {inner_exc}. Original error: {exc}")

    def _run_audit_internal(self, audit_id: str, mode_override: str | None = None) -> None:
        """Internal audit execution logic (separated for top-level exception handling)."""
        with self.session_factory() as db:
            audit = self.get_audit(db, audit_id)
            audit.status = "running"
            audit.started_at = datetime.now(UTC)
            if mode_override:
                audit.mode = mode_override
            db.add(
                AuditEvent(
                    audit_id=audit.id,
                    phase="start",
                    status="running",
                    message="Audit execution started.",
                    progress=5,
                    details={"target_url": audit.target_url, "mode": audit.mode},
                )
            )
            db.commit()

            target_url = audit.target_url
            scenarios = audit.selected_scenarios
            personas = audit.selected_personas

        browser_provider = get_browser_provider(mode_override)
        classifier_provider = get_classifier_provider(mode_override)

        try:
            run_result = browser_provider.run_audit(
                audit_id=audit_id,
                target_url=target_url,
                scenarios=scenarios,
                personas=personas,
                progress=lambda phase, message, value, status, details: self.emit_event(
                    audit_id,
                    phase,
                    message,
                    value,
                    status=status,
                    details=details,
                ),
            )
        except Exception as exc:
            fallback_provider = get_fallback_browser_provider()
            self.emit_event(
                audit_id,
                "fallback",
                f"Real browser path degraded gracefully to mock mode: {exc.__class__.__name__}",
                10,
                status="warning",
                details={"reason": str(exc)},
            )
            run_result = fallback_provider.run_audit(
                audit_id=audit_id,
                target_url=target_url,
                scenarios=scenarios,
                personas=personas,
                progress=lambda phase, message, value, status, details: self.emit_event(
                    audit_id,
                    phase,
                    message,
                    value,
                    status=status,
                    details=details,
                ),
            )

        drafts = []
        for observation in run_result.observations:
            drafts.extend(build_rule_findings(observation))
        drafts = self._merge_drafts(drafts)

        self.emit_event(
            audit_id,
            "detectors",
            f"Rule engine generated {len(drafts)} candidate findings.",
            62,
            status="running",
            details={"finding_count": len(drafts)},
        )

        finding_models: list[Finding] = []
        for index, draft in enumerate(drafts, start=1):
            classified = classifier_provider.classify(draft)
            finding_models.append(
                Finding(
                    audit_id=audit_id,
                    scenario=draft.scenario,
                    persona=draft.persona,
                    pattern_family=draft.pattern_family,
                    severity=classified.severity,
                    title=draft.title,
                    explanation=classified.explanation,
                    remediation=classified.remediation,
                    evidence_excerpt=draft.evidence_excerpt,
                    rule_reason=draft.rule_reason,
                    evidence_payload=draft.evidence_payload,
                    confidence=classified.confidence,
                    trust_impact=draft.trust_impact,
                    order_index=index,
                )
            )

        metrics = self._build_metrics(run_result.summary, run_result.observations, finding_models)
        trust_score, risk_level = self._score_audit(finding_models, metrics)
        summary = self._build_summary(finding_models, metrics)
        report_service = ReportService(get_storage_provider())

        with self.session_factory() as db:
            audit = self.get_audit(db, audit_id)
            audit.raw_run = {
                "provider_summary": run_result.summary,
                "observation_count": len(run_result.observations),
            }
            audit.metrics = metrics
            audit.summary = summary
            audit.trust_score = trust_score
            audit.risk_level = risk_level
            audit.status = "completed"
            audit.completed_at = datetime.now(UTC)
            audit.findings.clear()
            db.add_all(finding_models)
            db.flush()

            absolute_report_path, report_public_url = report_service.generate_report(audit, finding_models, metrics)
            audit.report_path = absolute_report_path
            audit.report_public_url = report_public_url
            db.add(
                AuditEvent(
                    audit_id=audit.id,
                    phase="report",
                    status="success",
                    message="Decision-ready HTML report generated.",
                    progress=100,
                    details={"report_url": report_public_url, "finding_count": len(finding_models)},
                )
            )
            db.commit()

    def emit_event(
        self,
        audit_id: str,
        phase: str,
        message: str,
        progress: int,
        status: str = "info",
        details: dict[str, Any] | None = None,
    ) -> None:
        with self.session_factory() as db:
            db.add(
                AuditEvent(
                    audit_id=audit_id,
                    phase=phase,
                    status=status,
                    message=message,
                    progress=progress,
                    details=details or {},
                )
            )
            db.commit()

    def get_audit(self, db: Session, audit_id: str) -> Audit:
        statement = (
            select(Audit).where(Audit.id == audit_id).options(selectinload(Audit.events), selectinload(Audit.findings))
        )
        audit = db.scalar(statement)
        if audit is None:
            raise ValueError(f"Audit {audit_id} not found")
        return audit

    @staticmethod
    def _build_metrics(summary: dict, observations: list, finding_models: list[Finding]) -> dict:
        site_host = observations[0].evidence.metadata.get("site_host") if observations else None
        evidence_origin_label = summary.get("evidence_origin_label", "Captured from site")
        persona_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "steps": [],
                "price_delta": 0.0,
                "finding_count": 0,
                "friction_index": 0,
                "notable_patterns": Counter(),
                "example": None,
            }
        )
        scenario_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"finding_count": 0, "patterns": Counter(), "example": None}
        )

        for observation in observations:
            metadata = observation.evidence.metadata
            if not metadata.get("scenario_state_found"):
                continue
            action_count = int(metadata.get("action_count", 0))
            price_delta = float(metadata.get("observed_price_delta", 0.0) or 0.0)
            persona_buckets[observation.persona]["steps"].append(action_count)
            persona_buckets[observation.persona]["price_delta"] += price_delta
            persona_buckets[observation.persona]["friction_index"] += action_count

        for finding in finding_models:
            persona_buckets[finding.persona]["finding_count"] += 1
            persona_buckets[finding.persona]["notable_patterns"][finding.pattern_family] += 1
            persona_buckets[finding.persona]["example"] = (
                persona_buckets[finding.persona]["example"] or finding.evidence_excerpt
            )
            scenario_buckets[finding.scenario]["finding_count"] += 1
            scenario_buckets[finding.scenario]["patterns"][finding.pattern_family] += 1
            scenario_buckets[finding.scenario]["example"] = (
                scenario_buckets[finding.scenario]["example"] or finding.evidence_excerpt
            )

        persona_comparison = []
        for persona, bucket in persona_buckets.items():
            average_steps = sum(bucket["steps"]) / max(1, len(bucket["steps"]))
            notable_patterns = [pattern for pattern, _ in bucket["notable_patterns"].most_common(3)]
            fallback = {
                "privacy_sensitive": "Privacy-first users followed a more cautious review path before committing.",
                "cost_sensitive": "Price-conscious users followed the most offer-driven checkout path.",
                "exit_intent": "Exit-intent behavior triggered the deepest review and policy path.",
            }[persona]
            headline = AuditOrchestrator._headline_from_example(bucket["example"], fallback)
            persona_comparison.append(
                {
                    "persona": persona,
                    "headline": headline,
                    "finding_count": bucket["finding_count"],
                    "friction_index": bucket["friction_index"],
                    "average_steps": round(average_steps, 1),
                    "price_delta": round(bucket["price_delta"], 2),
                    "notable_patterns": notable_patterns,
                }
            )

        scenario_breakdown = []
        for scenario, bucket in scenario_buckets.items():
            finding_count = bucket["finding_count"]
            risk_level = "critical" if finding_count >= 5 else "high" if finding_count >= 3 else "medium"
            dominant_patterns = [pattern for pattern, _ in bucket["patterns"].most_common(3)]
            fallback = {
                "cookie_consent": "The consent journey captured a trust-impacting choice imbalance.",
                "checkout_flow": "The checkout journey required additional offer, detail, or reserve steps after intent was established.",
                "subscription_cancellation": "The cancellation journey captured friction before a clean exit path.",
                "account_deletion": "The account deletion journey captured friction before a clean exit path.",
                "newsletter_signup": "The newsletter signup journey captured potential dark enrollment patterns.",
                "pricing_comparison": "The pricing comparison journey captured potential deceptive pricing patterns.",
            }.get(scenario, "Journey shows trust-impacting friction.")
            headline = AuditOrchestrator._headline_from_example(bucket["example"], fallback)
            scenario_breakdown.append(
                {
                    "scenario": scenario,
                    "headline": headline,
                    "risk_level": risk_level,
                    "finding_count": finding_count,
                    "dominant_patterns": dominant_patterns,
                }
            )

        return {
            "provider_summary": summary,
            "site_host": site_host,
            "evidence_origin_label": evidence_origin_label,
            "persona_comparison": sorted(persona_comparison, key=lambda item: item["finding_count"], reverse=True),
            "scenario_breakdown": sorted(scenario_breakdown, key=lambda item: item["finding_count"], reverse=True),
            "finding_count": len(finding_models),
            "observation_count": len(observations),
        }

    @staticmethod
    def _score_audit(findings: list[Finding], metrics: dict) -> tuple[float, str]:
        severity_weights = {"low": 2.0, "medium": 5.0, "high": 9.0, "critical": 14.0}
        deduction = sum(severity_weights.get(finding.severity, 5.0) + finding.trust_impact for finding in findings)
        friction_penalty = sum(item["friction_index"] for item in metrics.get("persona_comparison", []))
        trust_score = max(12.0, 100.0 - deduction - friction_penalty)
        if trust_score >= 82:
            risk_level = "low"
        elif trust_score >= 64:
            risk_level = "moderate"
        elif trust_score >= 42:
            risk_level = "high"
        else:
            risk_level = "critical"
        return round(trust_score, 1), risk_level

    @staticmethod
    def _build_summary(findings: list[Finding], metrics: dict) -> str:
        if not findings:
            return "No major trust risks were detected in the audited journeys."
        top_finding = max(findings, key=lambda finding: (finding.trust_impact, finding.confidence))
        riskiest_scenario = next(iter(metrics.get("scenario_breakdown", [])), {}).get("scenario", "the audited flows")
        site_host = metrics.get("site_host") or "the audited site"
        evidence_origin_label = metrics.get("evidence_origin_label", "Captured from site")
        return (
            f"{evidence_origin_label} evidence on {site_host} showed the clearest trust risk in "
            f"{riskiest_scenario.replace('_', ' ')}. The strongest observed signal was "
            f'"{top_finding.evidence_excerpt[:160]}", and persona comparisons still showed materially different friction across the run.'
        )

    @staticmethod
    def _merge_drafts(drafts: list[RuleFindingDraft]) -> list[RuleFindingDraft]:
        merged: dict[tuple[str, str, str], RuleFindingDraft] = {}
        for draft in drafts:
            key = (draft.scenario, draft.persona, draft.pattern_family)
            existing = merged.get(key)
            if not existing:
                merged[key] = draft
                continue

            existing.severity = AuditOrchestrator._max_severity(existing.severity, draft.severity)
            existing.trust_impact = max(existing.trust_impact, draft.trust_impact)
            if len(draft.evidence_excerpt) > len(existing.evidence_excerpt):
                existing.evidence_excerpt = draft.evidence_excerpt
            if len(draft.rule_reason) > len(existing.rule_reason):
                existing.rule_reason = draft.rule_reason
            existing.evidence_payload["supporting_evidence"] = AuditOrchestrator._merge_unique_strings(
                existing.evidence_payload.get("supporting_evidence", []),
                draft.evidence_payload.get("supporting_evidence", []),
            )
            existing.evidence_payload["matched_buttons"] = AuditOrchestrator._merge_unique_strings(
                existing.evidence_payload.get("matched_buttons", []),
                draft.evidence_payload.get("matched_buttons", []),
            )
            existing.evidence_payload["matched_prices"] = AuditOrchestrator._merge_unique_prices(
                existing.evidence_payload.get("matched_prices", []),
                draft.evidence_payload.get("matched_prices", []),
            )
        return list(merged.values())

    @staticmethod
    def _headline_from_example(example: str | None, fallback: str) -> str:
        if not example:
            return fallback
        clean = " ".join(example.split()).strip()[:120]
        return f'{fallback} Example captured evidence: "{clean}".'

    @staticmethod
    def _max_severity(first: str, second: str) -> str:
        severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return first if severity_rank.get(first, 1) >= severity_rank.get(second, 1) else second

    @staticmethod
    def _merge_unique_strings(first: list[str], second: list[str], limit: int = 6) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in first + second:
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _merge_unique_prices(first: list[dict], second: list[dict], limit: int = 4) -> list[dict]:
        result: list[dict] = []
        seen: set[tuple[str, float]] = set()
        for item in first + second:
            key = (str(item.get("label", "")), float(item.get("value", 0)))
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
            if len(result) >= limit:
                break
        return result
