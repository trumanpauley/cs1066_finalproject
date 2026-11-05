"""PitchIQ — AI Baseball Scouting Assistant (V0.4: minimal chat UI).

Run with:  streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from pitchiq.config import APP_ICON, APP_NAME, APP_TAGLINE
from pitchiq.state import init_state
from pitchiq.styles import inject_css
from pitchiq.ui.extracted import render_extracted_data
from pitchiq.ui.pitcher_profile import render_pitcher_profile
from pitchiq.ui.scout import render_scout
from pitchiq.ui.scouting_report import render_scouting_report
from pitchiq.ui.uploads import render_uploads

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.svg"


def _scout_page() -> None:
    render_scout()


def _arsenal_page() -> None:
    render_pitcher_profile()


def _library_page() -> None:
    render_uploads()
    st.divider()
    render_extracted_data()
    st.divider()
    render_scouting_report()


def main() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} — {APP_TAGLINE}",
        page_icon=APP_ICON,
        layout="centered",
        initial_sidebar_state="expanded",
    )
    init_state()
    inject_css()
    if _LOGO_PATH.exists():
        st.logo(str(_LOGO_PATH), size="large")

    pages = [
        st.Page(_scout_page, title="Scout", icon=":material/stylus_note:",
                url_path="scout", default=True),
        st.Page(_arsenal_page, title="My Arsenal", icon=":material/sports_baseball:",
                url_path="arsenal"),
        st.Page(_library_page, title="Scouting Library", icon=":material/folder_open:",
                url_path="library"),
    ]
    nav = st.navigation(pages)
    nav.run()

    st.markdown(
        '<div class="pitchiq-footer">PitchIQ — demo build. Responses are '
        "placeholders; report extraction and AI generation arrive in future "
        "iterations.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
