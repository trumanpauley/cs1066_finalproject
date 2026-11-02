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


def answer_scouting_question(
    question: str,
    pitcher_profile: dict[str, Any],
    analysis_depth: str,
    pitcher_reports: list[dict] | None = None,
    opponent_reports: list[dict] | None = None,
) -> dict:
    """Answer a scouting question for the Scout workspace.

    V0.3: a placeholder engine that assembles answers from sample data.
    Future versions keep this exact signature and swap the internals for:
      1. retrieval of relevant chunks from uploaded PDFs (RAG),
      2. an LLM call grounded in the pitcher profile + retrieved context.

    Returns a dict: `answer` (markdown), `context_used` (list[str]),
    and `depth`.
    """
    q = question.lower()

    # Naive hitter matching — the future RAG retriever replaces this.
    matched = [
        h for h in SAMPLE_HITTERS
        if any(part.lower() in q for part in h["name"].split())
    ]
    targets = matched or SAMPLE_HITTERS

    # Describe which context sources informed this answer.
    context_used: list[str] = []
    arsenal = pitcher_profile.get("arsenal") or []
    if arsenal:
        pitch_list = ", ".join(p["pitch"] for p in arsenal)
        context_used.append(f"Your profile ({pitch_list})")
    if pitcher_reports:
        context_used.extend(f"📎 {r['name']}" for r in pitcher_reports)
    if opponent_reports:
        context_used.extend(f"📎 {r['name']}" for r in opponent_reports)
    if not opponent_reports:
        context_used.append("Sample lineup (fictional demo data)")

    # Assemble the markdown answer at the requested depth.
    lines: list[str] = []
    if matched:
        lines.append(f"Here's the plan for **{matched[0]['name']}**:")
    else:
        lines.append(
            f"Here's a **{analysis_depth.lower()}** game plan for the opposing lineup:"
        )
    lines.append("")

    for h in targets:
        rec = h["recommendations"][analysis_depth]
        if analysis_depth == "Quick":
            lines.append(f"- **#{h['number']} {h['name']}** ({h['bats']}): {rec}")
        else:
            lines.append(f"**#{h['number']} {h['name']}** — bats {h['bats']}, {h['threat'].lower()} threat")
            if analysis_depth == "Detailed":
                lines.append(f"*{h['summary']}*")
            lines.append(f"> {rec}")
            lines.append("")

    hand = pitcher_profile.get("throwing_hand")
    if arsenal and hand:
        best = max(arsenal, key=lambda p: p.get("usage_pct", 0))
        lines.append("")
        lines.append(
            f"⚙️ Tailored to your profile: as a {hand.split(' ')[0].lower()}-hander "
            f"leaning on your **{best['pitch']}** ({best.get('usage_pct', 0)}% usage), "
            "these sequences play to your strengths."
        )

    lines.append("")
    lines.append(
        "_🔮 V0.3 preview: this plan is built from sample data. Once RAG and AI "
        "generation land, answers will be grounded in your uploaded reports._"
    )

    return {
        "answer": "\n".join(lines),
        "context_used": context_used,
        "depth": analysis_depth,
    }
