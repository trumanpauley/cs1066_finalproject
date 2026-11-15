"""Simulate page: face an MLB team's lineup, one hitter at a time.

Pick an opponent and the hitters you'll face; each hitter's swing, chase,
contact, and batted-ball tendencies are built from his own Baseball Savant
pitches vs. your throwing hand (pitchiq/mlb/sim_profile.py). Your pitches
come from My Arsenal.

The game itself is the React/TypeScript app in `simulator/`, compiled into
`pitchiq/static/simulator.html` so the app never needs Node. Rebuild after
changing it:  cd simulator && npm install && npm run build
Every pitch is simulated in the browser — no server round-trips or LLM calls.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from pitchiq.mlb import sources
from pitchiq.mlb.hitter_profile import hand_code
from pitchiq.mlb.sim_profile import simulator_hitter, simulator_pitcher
from pitchiq.state import profile_complete
from pitchiq.ui.hitter_card import CURRENT_SEASON, get_profile

_BUILD = Path(__file__).resolve().parent.parent / "static" / "simulator.html"
_HEIGHT = 1000
DEFAULT_TEAM_ID = 158  # Milwaukee Brewers, same default as Team Matchup


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _teams(season: int) -> list[dict]:
    return sources.list_teams(season)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _roster(team_id: int, season: int) -> list[dict]:
    return sources.team_hitters(team_id, season)


@st.cache_data(show_spinner=False)
def _load_build(mtime: float) -> str:
    # mtime is part of the cache key so a rebuild is picked up immediately.
    return _BUILD.read_text(encoding="utf-8")


def render_simulator() -> None:
    st.markdown("## Simulate")
    st.caption(
        "Face a lineup batter by batter. Pick a pitch, click where to aim, and throw — "
        "each hitter swings, chases, and makes contact at the rates in his Baseball "
        "Savant data against your throwing hand."
    )

    if not _BUILD.exists():
        st.warning("The simulator hasn't been built yet. Run "
                   "`cd simulator && npm install && npm run build`, then refresh.")
        return

    if profile_complete():
        hand = hand_code(st.session_state.throwing_hand)
        pitcher = simulator_pitcher(st.session_state.arsenal, st.session_state.throwing_hand,
                                    st.session_state.pitcher_name)
    else:
        st.info("No arsenal on **My Arsenal** yet — you'll pitch with a sample right-hander "
                "(four-seam, slider, changeup) until you add your own pitches.")
        hand, pitcher = "R", None

    lineup = _lineup_picker(hand)
    # The scoreboard is narrow: show "MIL", not "Milwaukee Brewers".
    data = {"hitters": lineup["hitters"] if lineup else [], "team": lineup.get("abbr", "") if lineup else ""}
    if pitcher:
        data["pitcher"] = pitcher
    if lineup and lineup.get("failed"):
        st.caption("Skipped: " + "; ".join(lineup["failed"]))
    if not data["hitters"]:
        st.caption("No lineup loaded — the simulator is using its two synthetic demo hitters.")

    st.iframe(_with_data(_load_build(_BUILD.stat().st_mtime), data), height=_HEIGHT)


def _lineup_picker(hand: str) -> dict | None:
    """Team + hitters selection; returns the loaded lineup (or None)."""
    season = CURRENT_SEASON
    try:
        teams = _teams(season)
    except Exception as exc:  # network / API problems shouldn't crash the app
        st.error(f"Couldn't load MLB teams: {exc}")
        return None
    names = {t["id"]: t["name"] for t in teams}
    abbrevs = {t["id"]: t["abbreviation"] for t in teams}
    ids = list(names)

    # Default to the team scouted on Team Matchup, so prep flows into practice.
    scouted = (st.session_state.get("team_matchup") or {}).get("team_id")
    default = scouted if scouted in ids else DEFAULT_TEAM_ID
    with st.container(border=True):
        team_id = st.selectbox("Opponent", ids, format_func=names.get,
                               index=ids.index(default) if default in ids else 0, key="sim_team")
        try:
            roster = _roster(team_id, season)
        except Exception as exc:
            st.error(f"Couldn't load the roster: {exc}")
            return None
        by_id = {h["id"]: {**h, "team": abbrevs[team_id]} for h in roster}
        chosen = st.multiselect(
            "Lineup (in batting order)", list(by_id), default=list(by_id)[:9], key=f"sim_hitters_{team_id}",
            format_func=lambda i: f"{by_id[i]['name']} ({by_id[i]['position']})",
            help="Hitters are faced in the order listed. Remove or re-add players to change the order.",
        )
        load = st.button("Load lineup", type="primary", disabled=not chosen)

    current = st.session_state.get("sim_lineup")
    if load:
        current = _load(team_id, names[team_id], season, hand, [by_id[i] for i in chosen])
        current["abbr"] = abbrevs[team_id]
        st.session_state.sim_lineup = current
    if current and current["hand"] != hand:
        st.warning("Your throwing hand changed since this lineup was loaded — click **Load lineup** again.")
        return None
    return current


def _load(team_id: int, team_name: str, season: int, hand: str, hitters: list[dict]) -> dict:
    loaded, failed = [], []
    with st.status(f"Loading {len(hitters)} hitters from Baseball Savant…", expanded=False) as status:
        for i, h in enumerate(hitters, 1):
            status.update(label=f"Loading {h['name']} ({i}/{len(hitters)})…")
            try:
                loaded.append(simulator_hitter(get_profile(h, season, hand), season))
            except Exception as exc:
                failed.append(f"{h['name']} ({exc})")
        status.update(label=f"Loaded {len(loaded)} hitters", state="complete")
    return {"team_id": team_id, "team": team_name, "hand": hand, "hitters": loaded, "failed": failed}


def _with_data(page: str, data: dict) -> str:
    """Inject the lineup + pitcher as window.PITCHIQ_DATA ahead of the app script."""
    payload = json.dumps(data).replace("</", "<\\/")
    return page.replace("<head>", f"<head><script>window.PITCHIQ_DATA = {payload};</script>", 1)
