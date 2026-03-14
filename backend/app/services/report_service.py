from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import PROJECT_ROOT
from app.models.audit import Audit, Finding
from app.providers.storage import StorageProvider


class ReportService:
    def __init__(self, storage: StorageProvider):
        template_dir = PROJECT_ROOT / "backend" / "app" / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.environment.filters["pretty_action"] = self._pretty_action
        self.environment.filters["pretty_path"] = self._pretty_path
        self.storage = storage

    def generate_report(self, audit: Audit, findings: list[Finding], metrics: dict[str, Any]) -> tuple[str | None, str]:
        template = self.environment.get_template("report.html")
        grouped_findings: dict[str, dict[str, list[Finding]]] = defaultdict(lambda: defaultdict(list))
        for finding in sorted(findings, key=lambda item: (item.scenario, item.persona, item.order_index)):
            grouped_findings[finding.scenario][finding.persona].append(finding)

        html = template.render(
            audit=audit,
            findings=findings,
            grouped_findings=grouped_findings,
            metrics=metrics,
            report_meta=self._build_report_meta(audit, findings, metrics),
        )
        saved = self.storage.save_text(
            f"reports/{audit.id}.html",
            html,
            "text/html; charset=utf-8",
        )
        return saved.absolute_path, saved.public_url

    def _build_report_meta(self, audit: Audit, findings: list[Finding], metrics: dict[str, Any]) -> dict[str, Any]:
        completed_at = audit.completed_at or audit.updated_at or audit.created_at
        return {
            "target_host": self._target_host(audit.target_url),
            "generated_at": self._format_timestamp(completed_at),
            "score_display": f"{round(audit.trust_score or 0)} / 100" if audit.trust_score is not None else "n/a",
            "risk_summary": self._risk_summary(audit.risk_level or "moderate"),
            "score_scale": [
                {"label": "Low risk", "range": "82-100"},
                {"label": "Moderate risk", "range": "64-81"},
                {"label": "High risk", "range": "42-63"},
                {"label": "Critical risk", "range": "0-41"},
            ],
            "persona_paths": self._persona_paths(findings),
            "finding_labels": {finding.id: self._evidence_label(finding) for finding in findings},
            "finding_paths": {
                finding.id: self._pretty_path(finding.evidence_payload.get("interacted_controls", []))
                for finding in findings
            },
            "finding_excerpts": {finding.id: self._display_excerpt(finding) for finding in findings},
        }

    @staticmethod
    def _target_host(target_url: str) -> str:
        try:
            return urlparse(target_url).netloc or target_url
        except Exception:
            return target_url

    @staticmethod
    def _format_timestamp(value: datetime | None) -> str:
        if value is None:
            return "Unknown"
        try:
            return value.strftime("%b %d, %Y %I:%M %p")
        except Exception:
            return str(value)

    @staticmethod
    def _risk_summary(risk_level: str) -> str:
        summaries = {
            "low": "Low risk: trust signals stayed stable across the audited journeys.",
            "moderate": "Moderate risk: some trust friction was observed, but it was not dominant.",
            "high": "High risk: trust friction was repeatedly observed in the audited journeys.",
            "critical": "Critical risk: the audited journeys repeatedly added friction before commitment or exit.",
        }
        return summaries.get(
            risk_level, "Risk level reflects how consistently friction or pressure appeared in the audited paths."
        )

    def _persona_paths(self, findings: list[Finding]) -> dict[str, str]:
        persona_paths: dict[str, str] = {}
        for finding in findings:
            if finding.persona in persona_paths:
                continue
            path = self._pretty_path(finding.evidence_payload.get("interacted_controls", []))
            if path:
                persona_paths[finding.persona] = path
        return persona_paths

    def _evidence_label(self, finding: Finding) -> str:
        if finding.evidence_payload.get("interacted_controls"):
            return "Observed evidence"
        if finding.evidence_payload.get("matched_quote"):
            return "Observed copy"
        if finding.evidence_payload.get("matched_prices"):
            return "Observed pricing"
        return "Observed evidence"

    def _pretty_path(self, actions: list[str] | None) -> str:
        if not actions:
            return ""
        return " -> ".join(self._pretty_action(action) for action in actions[:4] if action)

    def _display_excerpt(self, finding: Finding) -> str:
        path = self._pretty_path(finding.evidence_payload.get("interacted_controls", []))
        excerpt = finding.evidence_excerpt
        if not path:
            return excerpt
        if "Friction signals:" in excerpt:
            suffix = excerpt.split("Friction signals:", 1)[1].strip()
            return f"{path}. Friction signals: {suffix}"
        if "scenario interactions were captured" in excerpt:
            return path
        return excerpt

    def _pretty_action(self, action: str) -> str:
        clean = " ".join(action.split()).strip()
        quoted = self._extract_quoted(clean)
        if clean.startswith('Selected offer "') and quoted:
            if not any(char.isdigit() for char in quoted) and len(quoted.split()) <= 4:
                return f"Selected destination {quoted}"
            return f"Selected offer {self._trim(quoted, 68)}"
        if clean.startswith('Opened hotel detail "') and quoted:
            return f"Opened hotel {self._trim(quoted, 68)}"
        if clean.startswith('Interacted with checkout control "') and quoted:
            return quoted
        return self._trim(clean, 80)

    @staticmethod
    def _extract_quoted(value: str) -> str:
        parts = value.split('"')
        return parts[1] if len(parts) >= 3 else value

    @staticmethod
    def _trim(value: str, limit: int) -> str:
        return value if len(value) <= limit else f"{value[: limit - 1].rstrip()}…"
