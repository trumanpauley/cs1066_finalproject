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

import re
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


# ---------------------------------------------------------------------------
# Scout workspace answer engine (demo implementation)
# ---------------------------------------------------------------------------

_PITCH_KEYWORDS: dict[str, str] = {
    "four-seam": "Four-Seam Fastball",
    "four seam": "Four-Seam Fastball",
    "fastball": "Fastball",
    "heater": "Fastball",
    "two-seam": "Sinker",
    "sinker": "Sinker",
    "cutter": "Cutter",
    "slider": "Slider",
    "sweeper": "Sweeper",
    "curve": "Curveball",
    "changeup": "ChangeUp",
    "change-up": "ChangeUp",
    "change up": "ChangeUp",
    "splitter": "Splitter",
    "knuckle": "Knuckleball",
}

_OPPONENT_PATTERN = re.compile(
    r"(?:pitch to|face|facing|against|attack|get out)\s+"
    r"([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+)+)"
)


def _pitches_from_question(question: str) -> list[str]:
    """Pull pitch names mentioned in the question (ordered, de-duplicated)."""
    q = question.lower()
    found: list[str] = []
    for keyword, pitch in _PITCH_KEYWORDS.items():
        if keyword in q and pitch not in found:
            found.append(pitch)
    # "four-seam" also matches "fastball"-free questions; drop generic
    # "Fastball" if the more specific four-seam variant was named.
    if "Four-Seam Fastball" in found and "Fastball" in found:
        found.remove("Fastball")
    return found


def _opponent_from_question(question: str) -> str | None:
    """Pull a capitalized full name the user asked about, if any."""
    match = _OPPONENT_PATTERN.search(question)
    return match.group(1).strip() if match else None


def answer_scouting_question(
    question: str,
    pitcher_profile: dict[str, Any],
    analysis_depth: str,
    pitcher_reports: list[dict] | None = None,
    opponent_reports: list[dict] | None = None,
    attachments: list[dict] | None = None,
) -> dict:
    """Answer a scouting question for the Scout workspace.

    V0.4: a clearly-labeled demo engine over sample data. Future versions keep
    this signature and swap the internals for RAG retrieval over uploaded
    reports plus an LLM call grounded in the pitcher profile.

    Returns a dict:
        answer (markdown), context_used (list[str]), depth (str),
        evidence (list of sample-hitter dicts backing the answer), demo (bool).
    """
    q = question.lower()

    # --- Determine the pitcher's working arsenal -----------------------------
    arsenal = pitcher_profile.get("arsenal") or []
    question_pitches = _pitches_from_question(question)
    if arsenal:
        pitch_names = [p["pitch"] for p in arsenal]
        arsenal_source = "profile"
    elif question_pitches:
        pitch_names = question_pitches
        arsenal_source = "question"
    else:
        pitch_names = []
        arsenal_source = None

    # --- Identify the target hitter(s) --------------------------------------
    matched = [
        h for h in SAMPLE_HITTERS
        if any(part.lower() in q for part in h["name"].split())
    ]
    named_opponent = None if matched else _opponent_from_question(question)

    # --- Describe answer context ---------------------------------------------
    context_used: list[str] = []
    if arsenal_source == "profile":
        context_used.append(f"Pitcher profile ({', '.join(pitch_names)})")
    elif arsenal_source == "question":
        context_used.append(f"Arsenal from your question ({', '.join(pitch_names)})")
    if pitcher_reports:
        context_used.extend(f"Uploaded report: {r['name']}" for r in pitcher_reports)
    if opponent_reports:
        context_used.extend(f"Uploaded report: {r['name']}" for r in opponent_reports)
    if attachments:
        context_used.extend(f"Chat attachment: {r['name']}" for r in attachments)
    context_used.append("Sample scouting data (demo)")

    # --- Assemble the answer --------------------------------------------------
    lines: list[str] = []
    evidence: list[dict] = []

    if named_opponent:
        # No data on this hitter — produce a general plan scaffold.
        lines.append(f"**Scouting plan: {named_opponent}**")
        lines.append("")
        lines.append(
            f"There's no report on {named_opponent} in your library yet, so here's "
            "a general approach to build on:"
        )
        lines.append("")
        if pitch_names:
            primary = pitch_names[0]
            secondaries = pitch_names[1:] or ["your secondary stuff"]
            lines.append(
                f"- **Establish the {primary.lower()}** early for strike one — "
                "command of your best pitch sets up everything else."
            )
            lines.append(
                f"- **Change eye levels and speeds** with "
                f"{', '.join(s.lower() for s in secondaries)} once you're ahead."
            )
            lines.append(
                "- **Finish off the barrel**: with two strikes, work just off the "
                "zone with your best swing-and-miss pitch rather than giving in."
            )
        else:
            lines.append(
                "- Mix speeds, change eye levels, and attack the edges — "
                "add your arsenal (in the question or on My Arsenal) for a "
                "pitch-specific sequence."
            )
        lines.append("")
        lines.append(
            f"Upload a scouting report that covers {named_opponent} to get "
            "tendencies-based recommendations here."
        )
    else:
        targets = matched or SAMPLE_HITTERS
        evidence = targets
        if matched:
            lines.append(f"**Scouting plan: {matched[0]['name']}**")
        else:
            lines.append(
                f"**{analysis_depth} game plan — opposing lineup** (sample data)"
            )
        lines.append("")
        for h in targets:
            rec = h["recommendations"][analysis_depth]
            if analysis_depth == "Quick":
                lines.append(f"- **#{h['number']} {h['name']}** ({h['bats']}): {rec}")
            else:
                lines.append(
                    f"**#{h['number']} {h['name']}** — bats {h['bats']}, "
                    f"{h['threat'].lower()} threat"
                )
                if analysis_depth == "Detailed":
                    lines.append(f"*{h['summary']}*")
                lines.append(f"> {rec}")
                lines.append("")

    hand = pitcher_profile.get("throwing_hand")
    if pitch_names and hand:
        lines.append("")
        lines.append(
            f"As a {hand.split(' ')[0].lower()}-hander working off your "
            f"**{pitch_names[0].lower()}**, these sequences play to your strengths."
        )

    return {
        "answer": "\n".join(lines),
        "context_used": context_used,
        "depth": analysis_depth,
        "evidence": evidence,
        "demo": True,
    }
