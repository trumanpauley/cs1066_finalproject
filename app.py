"""PitchIQ — MLB hitter scouting for a pitcher's own arsenal (V0.6).

Run with:  streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from pitchiq.config import APP_ICON, APP_NAME, APP_TAGLINE
from pitchiq.state import init_state
from pitchiq.styles import inject_css
from pitchiq.ui.pitcher_profile import render_pitcher_profile
from pitchiq.ui.scout import render_scout
from pitchiq.ui.team_matchup import render_team_matchup

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.svg"


def _scout_page() -> None:
    render_scout()


def _arsenal_page() -> None:
    render_pitcher_profile()


def _team_page() -> None:
    render_team_matchup()


# The Scouting Library (PDF uploads + extraction: pitchiq/ui/uploads.py,
# extracted.py) is hidden while the app focuses on MLB hitters. To bring it
# back, add a page that calls render_uploads() and render_extracted_data().


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
        st.Page(_team_page, title="Team Matchup", icon=":material/stadium:",
                url_path="team"),
        st.Page(_arsenal_page, title="My Arsenal", icon=":material/sports_baseball:",
                url_path="arsenal"),
    ]
    nav = st.navigation(pages)
    nav.run()

    st.markdown(
        '<div class="pitchiq-footer">PitchIQ — data from Baseball Savant '
        "(public Statcast). Game plans are rule-based from the numbers shown.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
