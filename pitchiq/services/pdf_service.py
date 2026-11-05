"""PDF ingestion service.

V0.1: validates uploads and records metadata only — file contents are kept
in memory so a future version can parse them.

Future iterations will implement `extract_report_data()` with a real PDF
parser (e.g., pdfplumber / PyMuPDF) that converts TruMedia-style report
pages into the structured hitter/pitcher dictionaries used by the UI.
"""

from __future__ import annotations

from typing import Any

from pitchiq.config import MAX_UPLOAD_MB


def validate_upload(uploaded_file: Any) -> tuple[bool, str]:
    """Check an uploaded file and return (ok, message)."""
    if uploaded_file is None:
        return False, "No file provided."
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        return False, f"File exceeds the {MAX_UPLOAD_MB} MB limit."
    if not uploaded_file.name.lower().endswith(".pdf"):
        return False, "Only PDF files are supported."
    return True, "File accepted."


def summarize_upload(uploaded_file: Any) -> dict:
    """Build the metadata record stored in session state for an upload."""
    return {
        "name": uploaded_file.name,
        "size_kb": round(uploaded_file.size / 1024, 1),
        "status": "Ready",
    }


def extract_report_data(uploaded_file: Any) -> dict:
    """Parse a scouting-report PDF into structured data.

    Detects the report format (pitcher process report, opponent statistical
    report, or opponent heatmap report) and dispatches to the matching parser
    in `pitchiq.extraction`. Returns a dict with `report_type`, parsed data,
    and an `errors` list (partial extractions still return data).
    """
    from pitchiq.extraction import extract_report

    return extract_report(uploaded_file.getvalue(), uploaded_file.name)


def extraction_summary(result: dict) -> str:
    """One-line description of an extraction result for upload status rows."""
    rt = result.get("report_type")
    if rt == "pitcher_report":
        return f"Pitcher report · {len(result.get('pitches', []))} pitches"
    if rt == "opponent_stats":
        return f"Stats report · {len(result.get('hitters', []))} hitters"
    if rt == "opponent_heatmap":
        return f"Heatmap report · {len(result.get('entries', []))} pages"
    return "Unrecognized format"
