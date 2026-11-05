"""Format detection and dispatch for scouting-report PDFs."""

from __future__ import annotations

import pymupdf

from pitchiq.extraction.heatmap_report import parse_heatmap_report
from pitchiq.extraction.opponent_stats import parse_opponent_stats
from pitchiq.extraction.pitcher_report import parse_pitcher_report


def detect_report_type(doc: pymupdf.Document) -> str:
    """Classify a PDF as one of the supported report formats."""
    text = doc[0].get_text()
    if "Pitching Report" in text and "Usg vL" in text:
        return "pitcher_report"
    if "FPSwing%" in text and "vs. RHP" in text:
        return "opponent_stats"
    if "Data pulled on" in text:
        return "opponent_heatmap"
    return "unknown"


def extract_report(pdf_bytes: bytes, filename: str = "") -> dict:
    """Extract structured data from a scouting-report PDF.

    Returns a dict with at least: report_type, filename, page_count, errors.
    Parser-specific keys are documented in each parser module.
    """
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # corrupt/unreadable file
        return {
            "report_type": "unknown",
            "filename": filename,
            "page_count": 0,
            "errors": [f"Could not open PDF: {exc}"],
        }

    try:
        report_type = detect_report_type(doc)
        if report_type == "pitcher_report":
            result = parse_pitcher_report(doc)
        elif report_type == "opponent_stats":
            result = parse_opponent_stats(doc)
        elif report_type == "opponent_heatmap":
            result = parse_heatmap_report(doc)
        else:
            result = {
                "errors": [
                    "Unrecognized report format. Supported formats: pitcher "
                    "process reports, opponent statistical reports, and "
                    "opponent heatmap reports."
                ]
            }
        result["report_type"] = report_type
        result["filename"] = filename
        result["page_count"] = len(doc)
        result.setdefault("errors", [])
        return result
    finally:
        doc.close()


def render_page_png(pdf_bytes: bytes, page_number: int, zoom: float = 2.0) -> bytes:
    """Render one PDF page (1-based) to PNG bytes — used to display original
    heatmaps without re-interpreting their values."""
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        page = doc[page_number - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        return pix.tobytes("png")
