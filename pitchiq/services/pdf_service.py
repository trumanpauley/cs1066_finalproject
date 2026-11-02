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
    """[FUTURE — V0.2] Parse a scouting-report PDF into structured data.

    Will return a dict matching the schema in
    `pitchiq.data.sample_data.SAMPLE_HITTERS` (opponent reports) or
    `DEFAULT_ARSENAL` (pitcher process reports).
    """
    raise NotImplementedError("PDF extraction ships in a future iteration.")
