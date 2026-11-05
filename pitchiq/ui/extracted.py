"""Extracted Data section for the Scouting Library.

Shows structured data parsed from uploaded PDFs: pitcher reports (editable
pitch table), opponent statistical reports (editable per-hitter split tables
with sample sizes and preserved missing values), and opponent heatmap reports
(original pages rendered as images — numerical values are never invented).
Extraction errors are surfaced per file, and edits write back to session
state so corrected data flows into future analysis.
"""

from __future__ import annotations

import streamlit as st

from pitchiq.extraction import render_page_png
from pitchiq.extraction.opponent_stats import STAT_COLUMNS

_TYPE_LABELS = {
    "pitcher_report": "Pitcher process report",
    "opponent_stats": "Opponent statistical report",
    "opponent_heatmap": "Opponent heatmap report",
    "unknown": "Unrecognized report",
}


def render_extracted_data() -> None:
    st.markdown("### Extracted Data")
    st.caption(
        "Structured data parsed from your uploaded reports. Review and correct "
        "values below — edits are kept for this session and will ground AI "
        "analysis in future versions. Extracted data stays local and is never "
        "committed to the repository."
    )

    cache = st.session_state.extraction_cache
    records = st.session_state.pitcher_reports + st.session_state.opponent_reports
    keys_in_use = [r["cache_key"] for r in records if r.get("cache_key") in cache]

    if not keys_in_use:
        st.info("Upload reports above to see extracted hitters, statistics, and heatmaps.")
        return

    for key in keys_in_use:
        result = cache[key]
        label = _TYPE_LABELS.get(result["report_type"], "Report")
        with st.expander(
            f"{result['filename']} — {label} ({result['page_count']} pages)",
            expanded=len(keys_in_use) == 1,
        ):
            for err in result.get("errors", []):
                st.warning(f"Extraction issue: {err}")

            if result["report_type"] == "pitcher_report":
                _render_pitcher_extraction(result, key)
            elif result["report_type"] == "opponent_stats":
                _render_stats_extraction(result, key)
            elif result["report_type"] == "opponent_heatmap":
                _render_heatmap_extraction(result, key)
            else:
                st.caption("No structured data could be extracted from this file.")


# ---------------------------------------------------------------------------
# Pitcher process report
# ---------------------------------------------------------------------------

def _render_pitcher_extraction(result: dict, key: str) -> None:
    meta = []
    if result.get("pitcher_name"):
        meta.append(f"**{result['pitcher_name']}**")
    if result.get("date_range"):
        meta.append(result["date_range"])
    if result.get("race_to_2k"):
        meta.append(f"Race to 2K: {result['race_to_2k']}")
    if result.get("first_pitch_strikes"):
        meta.append(f"First-pitch strikes: {result['first_pitch_strikes']}")
    if meta:
        st.markdown(" · ".join(meta))

    edited = st.data_editor(
        result["pitches"],
        key=f"edit_pitches_{key}",
        width="stretch",
        hide_index=True,
        column_config={
            "code": st.column_config.TextColumn("Code"),
            "name": st.column_config.TextColumn("Pitch"),
            "velo_low": st.column_config.NumberColumn("Velo low"),
            "velo_high": st.column_config.NumberColumn("Velo high"),
            "velo_avg": st.column_config.NumberColumn("Velo avg"),
            "usage_count": st.column_config.NumberColumn("Count"),
            "usage_pct": st.column_config.NumberColumn("Usage %"),
            "spin_eff": st.column_config.NumberColumn("Spin eff"),
            "ivb": st.column_config.NumberColumn("IVB", format="%.1f"),
            "hb": st.column_config.NumberColumn("HB", format="%.1f"),
            "source_page": st.column_config.NumberColumn("Page", disabled=True),
        },
    )
    result["pitches"] = edited
    st.caption(
        "Blank cells were empty in the original report (e.g. Spin eff). "
        "Apply this arsenal from the My Arsenal page."
    )


# ---------------------------------------------------------------------------
# Opponent statistical report
# ---------------------------------------------------------------------------

def _render_stats_extraction(result: dict, key: str) -> None:
    hitters = result.get("hitters", [])
    if not hitters:
        st.caption("No hitters extracted.")
        return

    options = {
        f"#{h['number']} {h['name']} ({h['bats'] or '?'}) — page {h['source_page']}": i
        for i, h in enumerate(hitters)
    }
    choice = st.selectbox(
        f"Hitter ({len(hitters)} extracted)",
        list(options),
        key=f"stats_hitter_{key}",
    )
    hitter = hitters[options[choice]]

    st.caption(
        f"Source: page {hitter['source_page']} of {result['filename']} · "
        "P = pitches seen (sample size). Blank cells were '-' in the report "
        "(no data) — they are preserved, not estimated."
    )

    for side in ("vs. RHP", "vs. LHP"):
        rows = hitter["splits"].get(side, [])
        st.markdown(f"**{side}**")
        if not rows:
            st.caption("No table found for this split.")
            continue
        edited = st.data_editor(
            rows,
            key=f"edit_{side}_{key}_{options[choice]}",
            width="stretch",
            hide_index=True,
            column_config={
                "Pitch": st.column_config.TextColumn("Pitch", disabled=True),
                "P": st.column_config.NumberColumn("P"),
                **{
                    c: st.column_config.NumberColumn(c, format="%.3f" if c in ("AVG", "ISO", "wOBA") else "%.1f")
                    for c in STAT_COLUMNS
                },
            },
        )
        hitter["splits"][side] = edited


# ---------------------------------------------------------------------------
# Opponent heatmap report
# ---------------------------------------------------------------------------

def _render_heatmap_extraction(result: dict, key: str) -> None:
    entries = result.get("entries", [])
    if not entries:
        st.caption("No heatmap pages identified.")
        return

    pdf_bytes = st.session_state.pdf_store.get(key)

    hitter_names = []
    for e in entries:
        label = f"#{e['number']} {e['name']} ({e['bats'] or '?'})"
        if label not in hitter_names:
            hitter_names.append(label)

    col_h, col_s = st.columns([3, 2])
    with col_h:
        chosen_hitter = st.selectbox(
            f"Hitter ({len(hitter_names)} identified)",
            hitter_names,
            key=f"hm_hitter_{key}",
        )
    matching = [
        e for e in entries
        if f"#{e['number']} {e['name']} ({e['bats'] or '?'})" == chosen_hitter
    ]
    with col_s:
        hands = [e["pitcher_hand"] for e in matching]
        chosen_hand = st.selectbox("vs. pitcher", hands, key=f"hm_hand_{key}")

    entry = next(e for e in matching if e["pitcher_hand"] == chosen_hand)
    st.caption(
        f"Page {entry['page_number']} of {result['filename']} · "
        f"Pitch types: {', '.join(entry['pitch_types']) or 'n/a'} · "
        f"Data pulled {entry['data_pulled'] or 'n/a'}. Original heatmaps shown "
        "as-is — PitchIQ does not convert them into numbers."
    )

    if pdf_bytes is None:
        st.warning("Original PDF is no longer available in this session; re-upload to view heatmaps.")
        return
    st.image(render_page_png(pdf_bytes, entry["page_number"]), width="stretch")
