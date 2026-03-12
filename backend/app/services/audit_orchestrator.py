from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from threading import Thread
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.detectors.rule_engine import build_rule_findings
from app.models import Audit, AuditEvent, Finding
from app.schemas.audit import AuditCreateRequest
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
        with self.session_factory() as db:
            audit = self.get_audit(db, audit_id)
            audit.status = "running"
            audit.started_at = datetime.now(timezone.utc)
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
            audit.completed_at = datetime.now(timezone.utc)
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
            select(Audit)
            .where(Audit.id == audit_id)
            .options(selectinload(Audit.events), selectinload(Audit.findings))
        )
        audit = db.scalar(statement)
        if audit is None:
            raise ValueError(f"Audit {audit_id} not found")
        return audit

    @staticmethod
    def _build_metrics(summary: dict, observations: list, finding_models: list[Finding]) -> dict:
        persona_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "steps": [],
                "price_delta": 0.0,
                "finding_count": 0,
                "friction_index": 0,
                "notable_patterns": Counter(),
            }
        )
        scenario_buckets: dict[str, dict[str, Any]] = defaultdict(lambda: {"finding_count": 0, "patterns": Counter()})

        for observation in observations:
            prices = [float(item["value"]) for item in observation.evidence.price_points if isinstance(item.get("value"), (float, int))]
            price_delta = prices[-1] - prices[0] if len(prices) >= 2 else 0.0
            persona_buckets[observation.persona]["steps"].append(observation.evidence.step_count)
            persona_buckets[observation.persona]["price_delta"] += price_delta
            persona_buckets[observation.persona]["friction_index"] += len(observation.evidence.friction_indicators)

        for finding in finding_models:
            persona_buckets[finding.persona]["finding_count"] += 1
            persona_buckets[finding.persona]["notable_patterns"][finding.pattern_family] += 1
            scenario_buckets[finding.scenario]["finding_count"] += 1
            scenario_buckets[finding.scenario]["patterns"][finding.pattern_family] += 1

        persona_comparison = []
        for persona, bucket in persona_buckets.items():
            average_steps = sum(bucket["steps"]) / max(1, len(bucket["steps"]))
            notable_patterns = [pattern for pattern, _ in bucket["notable_patterns"].most_common(3)]
            headline = {
                "privacy_sensitive": "Privacy-first users encounter more pressure around consent and data persistence.",
                "cost_sensitive": "Price-conscious users see stronger fee surprises and discount-linked persuasion.",
                "exit_intent": "Exit-intent behavior triggers extra retention friction and emotionally loaded copy.",
            }[persona]
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
            headline = {
                "cookie_consent": "Consent surfaces emphasize acceptance and obscure the lowest-friction refusal path.",
                "checkout_flow": "Checkout introduces persuasion and cost changes after commitment begins.",
                "cancellation_flow": "Cancellation adds detours and retention pressure before users can exit cleanly.",
            }.get(scenario, "Journey shows trust-impacting friction.")
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
        dominant = Counter(finding.pattern_family for finding in findings).most_common(2)
        patterns = ", ".join(pattern.replace("_", " ") for pattern, _ in dominant)
        riskiest_scenario = next(iter(metrics.get("scenario_breakdown", [])), {}).get("scenario", "the audited flows")
        return (
            f"Highest trust risk concentrates in {riskiest_scenario.replace('_', ' ')}, "
            f"driven primarily by {patterns}. Persona comparisons show materially different levels of friction and persuasion."
        )
