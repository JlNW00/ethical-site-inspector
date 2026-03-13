"""PDF generation service for audit reports.

Provides functionality to convert HTML reports to PDF format using xhtml2pdf.
"""

from __future__ import annotations

from io import BytesIO

from xhtml2pdf import pisa


def generate_pdf_from_html(html_content: str) -> bytes:
    """Convert HTML content to PDF bytes.

    Args:
        html_content: HTML string to convert to PDF

    Returns:
        PDF file as bytes

    Raises:
        RuntimeError: If PDF generation fails
    """
    result = BytesIO()
    pdf = pisa.CreatePDF(html_content, dest=result)

    if pdf.err:
        raise RuntimeError(f"PDF generation failed with {pdf.err} errors")

    result.seek(0)
    return result.getvalue()
