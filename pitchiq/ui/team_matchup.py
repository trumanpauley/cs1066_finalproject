"""Game Plan page (home): a plan for every hitter on one MLB team, then practice it in Simulate."""

from __future__ import annotations

import streamlit as st

from pitchiq.config import ANALYSIS_MODES
from pitchiq.mlb import sources
from pitchiq.mlb.game_plan import threat_level
from pitchiq.mlb.hitter_profile import hand_code
from pitchiq.navigation import PAGES
from pitchiq.state import profile_complete
from pitchiq.ui.hitter_card import CURRENT_SEASON, GLOSSARY, get_profile, render_hitter_card

DEFAULT_TEAM_ID = 158  # Milwaukee Brewers
_THREAT_ORDER = {"High": 0, "Medium": 1, "Low": 2}


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _teams(season: int) -> list[dict]:
    return sources.list_teams(season)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _roster(team_id: int, season: int) -> list[dict]:
    return sources.team_hitters(team_id, season)


def render_team_matchup() -> None:
    st.markdown("## Game Plan")
    st.caption("Pick your opponent: get a plan for every hitter, ordered from most to "
               "least dangerous, then practice it against them in **Simulate**.")

    if profile_complete():
        hand = hand_code(st.session_state.throwing_hand)
    else:
        st.info("No arsenal on **My Arsenal** yet — plans show each hitter's tendencies only. "
                "Add your pitches to get pitch-by-pitch recommendations.")
        picked = st.segmented_control("Facing", ["vs RHP", "vs LHP"], default="vs RHP",
                                      key="team_hand", label_visibility="collapsed")
        hand = "L" if picked == "vs LHP" else "R"
    season = CURRENT_SEASON

    try:
        teams = _teams(season)
    except Exception as exc:  # network / API problems shouldn't crash the app
        st.error(f"Couldn't load MLB teams: {exc}")
        return
    names = {t["id"]: t["name"] for t in teams}
    abbrevs = {t["id"]: t["abbreviation"] for t in teams}
    ids = list(names)
    team_id = st.selectbox("Opponent", ids, format_func=names.get,
                           index=ids.index(DEFAULT_TEAM_ID) if DEFAULT_TEAM_ID in ids else 0)

    try:
        hitters = _roster(team_id, season)
    except Exception as exc:
        st.error(f"Couldn't load the roster: {exc}")
        return
    by_id = {h["id"]: {**h, "team": abbrevs[team_id]} for h in hitters}
    chosen = st.multiselect(
        "Hitters", list(by_id), default=list(by_id),
        format_func=lambda i: f"{by_id[i]['name']} ({by_id[i]['position']})",
        help="Active roster position players. Remove anyone you won't face.",
    )

    if st.button("Build game plan", type="primary", disabled=not chosen):
        # Simulate defaults its opponent to this team; drop its old pick so it follows.
        st.session_state.pop("sim_team", None)
        st.session_state.team_matchup = _load(team_id, names[team_id], season, hand,
                                              [by_id[i] for i in chosen])

    data = st.session_state.team_matchup
    if not data:
        return
    if data["hand"] != hand:
        st.warning("Your throwing hand changed since this plan was built — click **Build game plan** again.")
        return
    if "simulate" in PAGES and st.button(f"Practice against the {data['team']} in Simulate",
                                         icon=":material/sports_esports:"):
        st.switch_page(PAGES["simulate"])
    _render(data)


def _load(team_id: int, team_name: str, season: int, hand: str, hitters: list[dict]) -> dict:
    profiles, failed = [], []
    with st.status(f"Loading {len(hitters)} hitters from Baseball Savant…", expanded=False) as status:
        for i, h in enumerate(hitters, 1):
            status.update(label=f"Loading {h['name']} ({i}/{len(hitters)})…")
            try:
                profiles.append(get_profile(h, season, hand))
            except Exception as exc:
                failed.append(f"{h['name']} ({exc})")
        status.update(label=f"Loaded {len(profiles)} hitters", state="complete")
    return {"team_id": team_id, "team": team_name, "season": season, "hand": hand,
            "profiles": profiles, "failed": failed}


def _render(data: dict) -> None:
    st.divider()
    mode = st.segmented_control("Report depth", list(ANALYSIS_MODES),
                                default=st.session_state.analysis_mode, key="team_depth")
    if mode:
        st.session_state.analysis_mode = mode
    mode = st.session_state.analysis_mode

    profiles = sorted(data["profiles"],
                      key=lambda p: (_THREAT_ORDER[threat_level(p)], -(p["xwoba"] or 0)))

    st.markdown(f"#### {data['team']} — {data['season']} vs {data['hand']}HP")
    for profile in profiles:
        arsenal = st.session_state.arsenal if profile_complete() else []
        render_hitter_card(profile, arsenal, mode)

    if data["failed"]:
        st.caption("Skipped: " + "; ".join(data["failed"]))
    st.caption(f"Data: Baseball Savant regular season, pitches from "
               f"{'right' if data['hand'] == 'R' else 'left'}-handers only. {GLOSSARY}")
