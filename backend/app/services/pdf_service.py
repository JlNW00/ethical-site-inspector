"""PDF generation service for audit reports.

Provides functionality to convert HTML reports to PDF format using xhtml2pdf.
"""

from __future__ import annotations

import re
from io import BytesIO

from xhtml2pdf import pisa


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


def generate_pdf_from_html(html_content: str) -> bytes:
    """Convert HTML content to PDF bytes.

    Args:
        html_content: HTML string to convert to PDF

    Returns:
        PDF file as bytes

    Raises:
        RuntimeError: If PDF generation fails
    """
    # xhtml2pdf cannot process CSS variables - inline them first
    processed_html = _inline_css_variables(html_content)

    result = BytesIO()
    pdf = pisa.CreatePDF(processed_html, dest=result)

    if pdf.err:
        raise RuntimeError(f"PDF generation failed with {pdf.err} errors")

    result.seek(0)
    return result.getvalue()
