"""PitchIQ — AI Baseball Scouting Application (V0.3: Scouting Workspace).

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from pitchiq.config import APP_ICON, APP_NAME, APP_TAGLINE, VERSION
from pitchiq.state import init_state
from pitchiq.styles import inject_css
from pitchiq.ui.pitcher_profile import render_pitcher_profile
from pitchiq.ui.scout import render_scout
from pitchiq.ui.scouting_report import render_scouting_report
from pitchiq.ui.sidebar import render_sidebar
from pitchiq.ui.uploads import render_uploads


def _scout_page() -> None:
    render_scout()


def _arsenal_page() -> None:
    render_pitcher_profile()


def _library_page() -> None:
    render_uploads()
    st.divider()
    render_scouting_report()


def main() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} — {APP_TAGLINE}",
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    inject_css()

    pages = [
        st.Page(_scout_page, title="Scout", icon="🎯", url_path="scout", default=True),
        st.Page(_arsenal_page, title="My Arsenal", icon="🧢", url_path="arsenal"),
        st.Page(_library_page, title="Scouting Library", icon="📚", url_path="library"),
    ]
    nav = st.navigation(pages)

    render_sidebar()

    # Full hero on the homepage; compact brand line on supporting pages.
    if nav.title == "Scout":
        st.markdown(
            f"""
            <div class="pitchiq-hero">
                <h1>{APP_ICON} {APP_NAME}</h1>
                <p>{APP_TAGLINE} — know every hitter before you throw a pitch.</p>
                <span class="version-badge">V{VERSION} · SCOUTING WORKSPACE</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    nav.run()

    st.markdown(
        '<div class="pitchiq-footer">PitchIQ · CS 1066 Final Project · '
        "V0.3 Scouting Workspace — PDF extraction, RAG, and AI-generated reports coming in future iterations.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
