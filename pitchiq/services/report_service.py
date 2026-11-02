"""Scouting-report generation service.

V0.1: returns curated sample data keyed by analysis mode, so the UI and the
future AI pipeline share one interface.

Future iterations will replace `generate_scouting_report()` internals with:
  1. retrieval over extracted PDF data (RAG),
  2. an LLM call that produces personalized recommendations from the
     pitcher's profile + opponent tendencies.
The function signature is designed to stay stable through that swap.
"""

from __future__ import annotations

from typing import Any

from pitchiq.data.sample_data import MODE_PREVIEWS, SAMPLE_HITTERS


def generate_scouting_report(
    pitcher_profile: dict[str, Any],
    opponent_data: list[dict] | None,
    analysis_mode: str,
) -> dict:
    """Produce a scouting report for the given pitcher vs. opponent lineup.

    Args:
        pitcher_profile: throwing hand, arsenal, strengths/weaknesses/preferences.
        opponent_data: structured hitter data (None in V0.1 → sample hitters).
        analysis_mode: "Quick" | "Standard" | "Detailed".

    Returns:
        dict with `mode_info` (header content) and `hitters` (list of hitter
        cards, each carrying the recommendation for the requested mode).
    """
    hitters = opponent_data or SAMPLE_HITTERS
    return {
        "mode_info": MODE_PREVIEWS[analysis_mode],
        "analysis_mode": analysis_mode,
        "pitcher_name": pitcher_profile.get("pitcher_name") or "Unnamed Pitcher",
        "hitters": hitters,
    }
