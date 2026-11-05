"""PDF scouting-report extraction for PitchIQ.

Modular parsers for the three supported report formats:

- Pitcher process reports (Sockeye/cwsdata): `pitcher_report.py`
- Opponent statistical reports (TruMedia grid): `opponent_stats.py`
- Opponent heatmap reports (TruMedia heatmaps): `heatmap_report.py`

`extract.py` detects the format and dispatches. All parsers return plain
dicts (session-state friendly, editable in the UI) and collect per-section
errors instead of raising, so partial extractions still surface. Future
formats plug in by adding a parser module and a detector rule; RAG indexing
can consume the same structured output.
"""

from pitchiq.extraction.extract import extract_report, render_page_png

__all__ = ["extract_report", "render_page_png"]
