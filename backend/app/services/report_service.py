from __future__ import annotations

from collections import defaultdict

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
        self.storage = storage

    def generate_report(self, audit: Audit, findings: list[Finding], metrics: dict) -> tuple[str | None, str]:
        template = self.environment.get_template("report.html")
        grouped_findings: dict[str, dict[str, list[Finding]]] = defaultdict(lambda: defaultdict(list))
        for finding in findings:
            grouped_findings[finding.scenario][finding.persona].append(finding)

        html = template.render(
            audit=audit,
            findings=findings,
            grouped_findings=grouped_findings,
            metrics=metrics,
        )
        saved = self.storage.save_text(
            f"reports/{audit.id}.html",
            html,
            "text/html; charset=utf-8",
        )
        return saved.absolute_path, saved.public_url
