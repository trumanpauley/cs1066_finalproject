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

import html
import json
import re
from pathlib import Path

import streamlit as st

from pitchiq.mlb import sources
from pitchiq.mlb.game_plan import build_game_plan
from pitchiq.mlb.hitter_profile import hand_code
from pitchiq.mlb.sim_profile import simulator_hitter, simulator_pitcher
from pitchiq.state import profile_complete
# The side panel reuses the Scout page's report pieces so both stay identical.
from pitchiq.ui.hitter_card import (
    CURRENT_SEASON,
    GLOSSARY,
    _arsenal_row,
    _pct,
    _tendency_rows,
    get_profile,
)

_BUILD = Path(__file__).resolve().parent.parent / "static" / "simulator.html"
_HEIGHT = 1060
DEFAULT_TEAM_ID = 158  # Milwaukee Brewers, same default as Game Plan
# MLB's public headshot images; unknown ids fall back to a generic silhouette.
HEADSHOT_URL = ("https://img.mlbstatic.com/mlb-photos/image/upload/"
                "d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{id}/headshot/67/current")


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
    # Wide layout on this page only: the game plus the scouting panel beside
    # it. styles.py caps .block-container at 880px app-wide, so lift it here.
    st.set_page_config(layout="wide")
    st.markdown("<style>.block-container { max-width: 1340px; }</style>", unsafe_allow_html=True)
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
    data = {"hitters": _with_reports(lineup, hand) if lineup else [],
            "team": lineup.get("abbr", "") if lineup else "",
            "glossary": GLOSSARY}
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

    # Default to the team scouted on Game Plan, so prep flows into practice.
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
    loaded, players, failed = [], [], []
    with st.status(f"Loading {len(hitters)} hitters from Baseball Savant…", expanded=False) as status:
        for i, h in enumerate(hitters, 1):
            status.update(label=f"Loading {h['name']} ({i}/{len(hitters)})…")
            try:
                loaded.append(simulator_hitter(get_profile(h, season, hand), season))
                players.append(h)
            except Exception as exc:
                failed.append(f"{h['name']} ({exc})")
        status.update(label=f"Loaded {len(loaded)} hitters", state="complete")
    return {"team_id": team_id, "team": team_name, "hand": hand, "season": season,
            "hitters": loaded, "players": players, "failed": failed}


def _with_reports(lineup: dict, hand: str) -> list[dict]:
    """Add each hitter's headshot and Scout-page report (built from the
    current My Arsenal, so edits there show up without reloading)."""
    players = lineup.get("players") or []
    season = lineup.get("season", CURRENT_SEASON)
    arsenal = st.session_state.arsenal if st.session_state.throwing_hand else []
    out = []
    for i, sim in enumerate(lineup["hitters"]):
        sim = dict(sim)
        if i < len(players):
            player = players[i]
            sim["photo"] = HEADSHOT_URL.format(id=int(player["id"]))
            try:
                sim["report"] = scout_report(get_profile(player, season, hand), arsenal)
            except Exception:  # a missing report shouldn't break the game
                pass
        out.append(sim)
    return out


_DETAIL_LINE = re.compile(r"^\s*<b>(.*?)</b>\s*(.*)$", re.S)


def _plain(text: str) -> str:
    """Game-plan text without its HTML tags."""
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def scout_report(profile: dict, arsenal: list[dict]) -> dict:
    """The Scout page's hitter card as data for the simulator's side panel."""
    card = build_game_plan(profile, arsenal)
    hand_label = f"{profile['pitcher_hand']}HP"
    recs = card["recommendations"]
    detailed = []
    for line in recs["Detailed"].split("<br>"):
        m = _DETAIL_LINE.match(line)
        if m:
            detailed.append({"label": _plain(m.group(1)).rstrip(":"), "text": _plain(m.group(2))})
        elif _plain(line):
            detailed.append({"label": "", "text": _plain(line)})
    o = profile["overall"]
    x = profile["xwoba"]
    bats = card["bats"] if card["bats"] != "S" else f"S (hits {card['stand']} vs {hand_label})"
    return {
        "number": str(profile.get("number") or ""),
        "meta": " · ".join(v for v in (profile.get("position", ""), profile.get("team", "")) if v),
        "bats": bats,
        "threat": card["threat"],
        "handLabel": hand_label,
        "summary": _plain(card["summary"]),
        "quick": _plain(recs["Quick"]),
        "standard": _plain(recs["Standard"]),
        "detailed": detailed,
        "hasArsenal": bool(arsenal),
        "metrics": [
            {"label": f"PA vs {hand_label}", "value": str(profile["pa"])},
            {"label": "xwOBA", "value": f"{x:.3f}".lstrip("0") if x is not None else "—"},
            {"label": "K%", "value": _pct(profile["k_pct"])},
            {"label": "BB%", "value": _pct(profile["bb_pct"])},
            {"label": "Chase%", "value": _pct(o["chase_pct"])},
            {"label": "Whiff%", "value": _pct(o["whiff_pct"])},
        ],
        "arsenalRows": [_arsenal_row(m, full=False) for m in card["matchups"]],
        "arsenalRowsFull": [_arsenal_row(m, full=True) for m in card["matchups"]],
        "tendencyRows": _tendency_rows(profile),
        "defaultDepth": st.session_state.get("analysis_mode", "Standard"),
    }


def _with_data(page: str, data: dict) -> str:
    """Inject the lineup + pitcher as window.PITCHIQ_DATA ahead of the app script."""
    payload = json.dumps(data).replace("</", "<\\/")
    return page.replace("<head>", f"<head><script>window.PITCHIQ_DATA = {payload};</script>", 1)
