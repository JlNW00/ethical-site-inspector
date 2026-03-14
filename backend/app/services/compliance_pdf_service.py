"""Compliance PDF generation service.

Provides functionality to generate regulatory compliance reports in PDF format.
Includes executive summary, per-regulation sections, compliance matrix,
and evidence references.
"""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.core.taxonomy import REGULATION_CITATIONS, REGULATION_FULL_NAMES
from app.models.audit import Audit, Finding


def _extract_css_variables(html_content: str) -> dict[str, str]:
    """Extract CSS variable definitions from :root block in HTML.

    Args:
        html_content: HTML string containing CSS

    Returns:
        Dictionary mapping variable names to their values
    """
    css_vars = {}
    # Match :root { ... } block
    root_match = re.search(r":root\s*\{([^}]+)\}", html_content, re.DOTALL)
    if root_match:
        root_content = root_match.group(1)
        # Match --variable-name: value; patterns
        var_pattern = r"--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);"
        for match in re.finditer(var_pattern, root_content):
            var_name = match.group(1)
            var_value = match.group(2).strip()
            css_vars[var_name] = var_value
    return css_vars


def _inline_css_variables(html_content: str) -> str:
    """Replace CSS var() references with their actual values.

    Args:
        html_content: HTML string containing CSS variables

    Returns:
        HTML with var() references replaced with hex values
    """
    css_vars = _extract_css_variables(html_content)

    # Replace var(--variable) with the actual value
    processed = html_content
    for var_name, var_value in css_vars.items():
        # Match var(--variable-name) with optional whitespace
        pattern = rf"var\(\s*--{re.escape(var_name)}\s*\)"
        processed = re.sub(pattern, var_value, processed)

    return processed


def _format_scenario_name(scenario: str) -> str:
    """Format a scenario key into a display name.

    Args:
        scenario: Scenario key like "cookie_consent"

    Returns:
        Display name like "Cookie Consent"
    """
    return scenario.replace("_", " ").title()


def _format_persona_name(persona: str) -> str:
    """Format a persona key into a display name.

    Args:
        persona: Persona key like "privacy_sensitive"

    Returns:
        Display name like "Privacy Sensitive"
    """
    return persona.replace("_", " ").title()


def _get_implicated_regulations(findings: list[Finding]) -> list[str]:
    """Get unique list of implicated regulations from findings.

    Args:
        findings: List of findings with regulatory_categories

    Returns:
        Sorted list of unique regulation abbreviations
    """
    regulations: set[str] = set()
    for finding in findings:
        for reg in finding.regulatory_categories:
            regulations.add(reg)
    return sorted(regulations)


def _get_findings_for_regulation(findings: list[Finding], regulation: str) -> list[Finding]:
    """Get findings that implicate a specific regulation.

    Args:
        findings: List of all findings
        regulation: Regulation abbreviation like "GDPR"

    Returns:
        List of findings that include this regulation
    """
    return [f for f in findings if regulation in f.regulatory_categories]


def _get_applicable_citations(finding: Finding, regulation: str) -> list[dict[str, str]]:
    """Get citation articles from this regulation applicable to the finding.

    Args:
        finding: The finding to get citations for
        regulation: Regulation abbreviation

    Returns:
        List of citation article strings
    """
    if regulation not in REGULATION_CITATIONS:
        return []

    # Get all citations for this regulation
    all_citations = REGULATION_CITATIONS[regulation]  # type: ignore[index]

    # For now, return the first 2 most relevant citations
    # In a more sophisticated system, we could match based on pattern family
    return all_citations[:2] if len(all_citations) >= 2 else all_citations


def _build_compliance_matrix(
    findings: list[Finding],
    scenarios: list[str],
    regulations: list[str],
) -> dict[str, Any]:
    """Build compliance matrix data structure.

    Args:
        findings: List of findings
        scenarios: List of scenario keys
        regulations: List of regulation abbreviations

    Returns:
        Matrix data structure for template rendering
    """
    rows = []
    for scenario in scenarios:
        row_cells = []
        for regulation in regulations:
            # Count findings for this scenario + regulation combination
            count = sum(1 for f in findings if f.scenario == scenario and regulation in f.regulatory_categories)
            row_cells.append({"regulation": regulation, "count": count})

        rows.append(
            {
                "scenario": _format_scenario_name(scenario),
                "cells": row_cells,
            }
        )

    return {
        "regulations": regulations,
        "rows": rows,
    }


def _build_evidence_references(findings: list[Finding]) -> list[dict[str, Any]]:
    """Build evidence references for template.

    Args:
        findings: List of findings with evidence

    Returns:
        List of evidence reference dicts
    """
    references = []
    for finding in findings:
        screenshot_urls = finding.evidence_payload.get("screenshot_urls", []) if finding.evidence_payload else []
        if screenshot_urls:
            references.append(
                {
                    "finding_title": finding.title,
                    "scenario": _format_scenario_name(finding.scenario),
                    "persona": _format_persona_name(finding.persona),
                    "screenshot_urls": screenshot_urls,
                }
            )
    return references


def _build_video_references(video_urls: dict[str, str] | None) -> list[dict[str, str]]:
    """Build video references for template.

    Args:
        video_urls: Dict mapping scenario_persona keys to URLs

    Returns:
        List of video reference dicts
    """
    if not video_urls:
        return []

    references = []
    for key, url in video_urls.items():
        # Parse scenario_persona key
        parts = key.rsplit("_", 1)
        if len(parts) == 2:
            scenario, persona = parts
            references.append(
                {
                    "scenario": _format_scenario_name(scenario),
                    "persona": _format_persona_name(persona),
                    "url": url,
                }
            )

    return references


def _generate_posture_statement(
    trust_score: float | None,
    total_findings: int,
    implicated_regulations: list[str],
) -> str:
    """Generate compliance posture statement.

    Args:
        trust_score: Trust score (0-100)
        total_findings: Number of regulatory findings
        implicated_regulations: List of implicated regulations

    Returns:
        Posture statement string
    """
    if trust_score is None:
        trust_score = 50.0

    if total_findings == 0:
        return (
            "No regulatory violations detected. The site appears to be in "
            "general compliance with applicable regulations."
        )

    if trust_score >= 80:
        base = (
            f"Overall favorable compliance posture with {total_findings} minor "
            f"regulatory observations across {len(implicated_regulations)} regulatory frameworks. "
        )
    elif trust_score >= 60:
        base = (
            f"Moderate compliance risk identified with {total_findings} findings "
            f"spanning {len(implicated_regulations)} regulations. "
        )
    elif trust_score >= 40:
        base = (
            f"Elevated compliance risk detected. {total_findings} significant findings "
            f"implicate {len(implicated_regulations)} regulatory frameworks. "
        )
    else:
        base = (
            f"High compliance risk. {total_findings} serious findings suggest "
            f"substantial non-compliance with {len(implicated_regulations)} regulations. "
        )

    recommendations = "Address high-severity findings first to mitigate legal exposure."
    return base + recommendations


def generate_compliance_pdf(audit: Audit, findings: list[Finding]) -> bytes:
    """Generate a regulatory compliance PDF report.

    Args:
        audit: The audit model with metadata
        findings: List of findings with regulatory_categories

    Returns:
        PDF file as bytes

    Raises:
        RuntimeError: If PDF generation fails
        ValueError: If audit has no regulatory findings
    """
    # Filter to only findings with regulatory categories
    regulatory_findings = [f for f in findings if f.regulatory_categories]

    if not regulatory_findings:
        raise ValueError("Audit has no findings with regulatory implications")

    # Get implicated regulations
    implicated_regulations = _get_implicated_regulations(regulatory_findings)

    # Build regulation sections
    regulation_sections = []
    for reg in implicated_regulations:
        reg_key = reg  # type: RegulationType
        reg_findings = _get_findings_for_regulation(regulatory_findings, reg)

        # Build finding data with applicable citations
        finding_data = []
        for finding in reg_findings:
            applicable_citations = _get_applicable_citations(finding, reg)
            citation_articles = [c["article"] for c in applicable_citations]

            finding_data.append(
                {
                    "title": finding.title,
                    "severity": finding.severity,
                    "explanation": finding.explanation,
                    "applicable_citations": citation_articles,
                }
            )

        # Get citations for this regulation
        citations = REGULATION_CITATIONS.get(reg_key, []) if reg in REGULATION_CITATIONS else []

        regulation_sections.append(
            {
                "abbreviation": reg,
                "full_name": REGULATION_FULL_NAMES.get(reg_key, reg),
                "citations": citations,
                "findings": finding_data,
            }
        )

    # Build compliance matrix
    matrix = _build_compliance_matrix(
        regulatory_findings,
        audit.selected_scenarios or [],
        implicated_regulations,
    )

    # Build evidence references
    evidence_references = _build_evidence_references(regulatory_findings)

    # Build video references
    video_references = _build_video_references(audit.video_urls)

    # Generate posture statement
    posture_statement = _generate_posture_statement(
        audit.trust_score,
        len(regulatory_findings),
        implicated_regulations,
    )

    # Prepare template context
    context = {
        "target_url": audit.target_url,
        "audit_date": audit.created_at.strftime("%Y-%m-%d %H:%M UTC") if audit.created_at else "N/A",
        "trust_score": f"{audit.trust_score:.0f}" if audit.trust_score else "N/A",
        "total_findings": len(regulatory_findings),
        "implicated_regulations": implicated_regulations,
        "posture_statement": posture_statement,
        "regulation_sections": regulation_sections,
        "matrix": matrix,
        "evidence_references": evidence_references,
        "video_references": video_references,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
    }

    # Load and render template
    templates_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("compliance_report.html")
    html_content = template.render(**context)

    # xhtml2pdf cannot process CSS variables - inline them first
    processed_html = _inline_css_variables(html_content)

    # Generate PDF
    result = BytesIO()
    pdf = pisa.CreatePDF(processed_html, dest=result)

    if pdf.err:
        # Log the HTML content for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"PDF generation failed with {pdf.err} errors")
        logger.error(f"HTML length: {len(processed_html)}")
        # Include first 1000 chars of HTML for debugging
        logger.error(f"HTML preview: {processed_html[:1000]}")
        raise RuntimeError(f"PDF generation failed with {pdf.err} errors")

    result.seek(0)
    return result.getvalue()
