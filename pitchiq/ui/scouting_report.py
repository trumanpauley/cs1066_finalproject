"""Example scouting report section: fictional hitters + recommendations.

Rendering adapts to the selected analysis mode (Quick / Standard / Detailed).
In V0.1 the data comes from `sample_data`; the same renderer will display
AI-generated reports in future versions.
"""

from __future__ import annotations

import streamlit as st

from pitchiq.services.report_service import generate_scouting_report

_THREAT_BADGES = {
    "High": '<span class="badge badge-high">High threat</span>',
    "Medium": '<span class="badge badge-medium">Medium threat</span>',
    "Low": '<span class="badge badge-low">Low threat</span>',
}


def render_scouting_report() -> None:
    st.markdown("### 📊 Example Scouting Report")
    st.caption(
        "A preview of what PitchIQ will generate. These hitters are fictional — "
        "future versions will build this report from your uploaded opponent PDFs "
        "and your pitcher profile."
    )

    mode = st.session_state.analysis_mode
    profile = {
        "pitcher_name": st.session_state.pitcher_name,
        "throwing_hand": st.session_state.throwing_hand,
        "arsenal": st.session_state.arsenal,
        "strengths": st.session_state.strengths,
        "weaknesses": st.session_state.weaknesses,
        "preferences": st.session_state.preferences,
    }
    report = generate_scouting_report(profile, opponent_data=None, analysis_mode=mode)

    # --- Mode header ----------------------------------------------------
    info = report["mode_info"]
    st.markdown(
        f'<div class="pitchiq-card"><h4>{info["title"]} <span class="badge badge-medium">'
        f'{mode} mode</span></h4><p>{info["body"]}</p>'
        f'<p style="color:#5b7083;font-size:0.88rem;">Includes: {" · ".join(info["sections"])}</p></div>',
        unsafe_allow_html=True,
    )

    # --- Hitter cards ----------------------------------------------------
    st.markdown("#### 🆚 Opposing Lineup — River City Riverhawks *(fictional)*")

    for hitter in report["hitters"]:
        _render_hitter(hitter, mode)

    st.caption(
        "📈 Stat glossary: P = pitches seen · FPSwing% = first-pitch swing rate · "
        "InZoneWhiff% = whiffs on in-zone pitches · Pre2K/2K-Ch% = chase rate before/with two strikes · "
        "SoftCt% = soft contact · wOBA = weighted on-base average."
    )


def _render_hitter(hitter: dict, mode: str) -> None:
    badge = _THREAT_BADGES.get(hitter["threat"], "")
    with st.container(border=True):
        st.markdown(
            f'<div class="hitter-header">'
            f'<span class="hitter-name">#{hitter["number"]} {hitter["name"]}</span>'
            f'<span class="hitter-meta">Bats: {hitter["bats"]}</span>{badge}</div>',
            unsafe_allow_html=True,
        )

        if mode in ("Standard", "Detailed"):
            st.markdown(f"*{hitter['summary']}*")

        st.markdown(
            f'<div class="rec-box"><span class="rec-label">How to attack</span><br>'
            f'{hitter["recommendations"][mode]}</div>',
            unsafe_allow_html=True,
        )

        if mode == "Standard":
            # Key stats only — one row per pitch, trimmed columns.
            trimmed = [
                {
                    "Pitch": s["Pitch"],
                    "InZoneWhiff%": s["InZoneWhiff%"],
                    "2K-Ch%": s["2K-Ch%"],
                    "Ground%": s["Ground%"],
                    "wOBA": s["wOBA"],
                }
                for s in hitter["stats"]
            ]
            st.dataframe(trimmed, width="stretch", hide_index=True)
        elif mode == "Detailed":
            st.dataframe(hitter["stats"], width="stretch", hide_index=True)
            weakest = min(hitter["stats"], key=lambda s: s["wOBA"])
            strongest = max(hitter["stats"], key=lambda s: s["wOBA"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Best pitch vs. him", weakest["Pitch"], f'{weakest["wOBA"]:.3f} wOBA')
            m2.metric("Most dangerous vs.", strongest["Pitch"], f'{strongest["wOBA"]:.3f} wOBA',
                      delta_color="inverse")
            m3.metric("Pitches scouted", sum(s["P"] for s in hitter["stats"]))
