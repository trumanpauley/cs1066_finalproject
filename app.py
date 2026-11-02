"""PitchIQ — AI Baseball Scouting Application (V0.2: Interactive UI).

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from pitchiq.config import APP_ICON, APP_NAME, APP_TAGLINE, VERSION
from pitchiq.state import init_state
from pitchiq.styles import inject_css
from pitchiq.ui.pitcher_profile import render_pitcher_profile
from pitchiq.ui.scouting_report import render_scouting_report
from pitchiq.ui.sidebar import render_sidebar
from pitchiq.ui.uploads import render_uploads


def main() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} — {APP_TAGLINE}",
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    inject_css()
    render_sidebar()

    # --- Hero banner ------------------------------------------------------
    st.markdown(
        f"""
        <div class="pitchiq-hero">
            <h1>{APP_ICON} {APP_NAME}</h1>
            <p>{APP_TAGLINE} — know every hitter before you throw a pitch.</p>
            <span class="version-badge">V{VERSION} · INTERACTIVE UI</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Main sections as tabs ---------------------------------------------
    tab_profile, tab_uploads, tab_report = st.tabs(
        ["🧢 Pitcher Profile", "📄 Upload Reports", "📊 Scouting Report"]
    )
    with tab_profile:
        render_pitcher_profile()
    with tab_uploads:
        render_uploads()
    with tab_report:
        render_scouting_report()

    st.markdown(
        '<div class="pitchiq-footer">PitchIQ · CS 1066 Final Project · '
        "V0.2 Interactive UI — PDF extraction, RAG, and AI-generated reports coming in future iterations.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
