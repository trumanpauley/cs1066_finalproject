"""PitchIQ — MLB hitter scouting for a pitcher's own arsenal (V0.7).

Run with:  streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from pitchiq.config import APP_ICON, APP_NAME, APP_TAGLINE
from pitchiq.state import init_state
from pitchiq.navigation import PAGES
from pitchiq.styles import inject_css
from pitchiq.ui.pitcher_profile import render_pitcher_profile
from pitchiq.ui.scout import render_scout
from pitchiq.ui.simulator import render_simulator
from pitchiq.ui.team_matchup import render_team_matchup

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.svg"


def _scout_page() -> None:
    render_scout()


def _arsenal_page() -> None:
    render_pitcher_profile()


def _team_page() -> None:
    render_team_matchup()


def _simulate_page() -> None:
    render_simulator()


# The Scouting Library (PDF uploads + extraction: pitchiq/ui/uploads.py,
# extracted.py) is hidden while the app focuses on MLB hitters. To bring it
# back, add a page that calls render_uploads() and render_extracted_data().


def main() -> None:
    st.set_page_config(
        page_title=f"{APP_NAME} — {APP_TAGLINE}",
        page_icon=APP_ICON,
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    init_state()
    inject_css()
    if _LOGO_PATH.exists():
        st.logo(str(_LOGO_PATH), size="large")

    # Main flow first: build a game plan for an opponent, then practice it in
    # the simulator. Hitter lookup and your arsenal are supporting pages.
    pages = [
        st.Page(_team_page, title="Game Plan", icon=":material/stadium:",
                url_path="plan", default=True),
        st.Page(_simulate_page, title="Simulate", icon=":material/sports_esports:",
                url_path="simulate"),
        st.Page(_scout_page, title="Hitter Lookup", icon=":material/person_search:",
                url_path="hitter"),
        st.Page(_arsenal_page, title="My Arsenal", icon=":material/sports_baseball:",
                url_path="arsenal"),
    ]
    PAGES.update({p.url_path: p for p in pages})
    nav = st.navigation(pages, position="top")
    nav.run()

    st.markdown(
        '<div class="pitchiq-footer">PitchIQ — data from Baseball Savant (public Statcast).</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
