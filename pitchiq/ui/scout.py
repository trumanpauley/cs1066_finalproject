"""Hitter Lookup page: search any MLB hitter, see his tendencies and a plan vs. your arsenal."""

from __future__ import annotations

import html

import streamlit as st

from pitchiq.config import ANALYSIS_MODES
from pitchiq.mlb import sources
from pitchiq.mlb.hitter_profile import hand_code
from pitchiq.ui.hitter_card import CURRENT_SEASON, GLOSSARY, get_profile, render_hitter_card

MAX_RECENT = 8


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _hitters(season: int) -> list[dict]:
    return sources.list_hitters(season)


def _label(h: dict) -> str:
    parts = [h["name"], h["position"], h["team"]]
    if h["bats"]:
        parts.append(f"Bats {h['bats']}")
    return " · ".join(p for p in parts if p)


def _select(hitter: dict) -> None:
    st.session_state.scout_current = hitter
    recent = [r for r in st.session_state.scout_recent if r["id"] != hitter["id"]]
    st.session_state.scout_recent = [hitter, *recent][:MAX_RECENT]


def _on_search(by_id: dict) -> None:
    picked = st.session_state.scout_search
    if picked is not None:
        _select(by_id[picked])
        st.session_state.scout_search = None  # clear the box for the next search


def _clear() -> None:
    st.session_state.scout_current = None
    st.session_state.scout_recent = []


def render_scout() -> None:
    current = st.session_state.scout_current
    st.markdown(
        f'<div class="scout-hero{" compact" if current else ""}">'
        "<h1>What&rsquo;s your game plan?</h1>"
        "<p>Search any MLB hitter. Build a plan around your arsenal.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    try:
        hitters = _hitters(CURRENT_SEASON)
    except Exception as exc:  # network / API problems shouldn't crash the app
        st.error(f"Couldn't load the MLB player list: {exc}")
        return
    by_id = {h["id"]: h for h in hitters}

    st.selectbox(
        "Search MLB hitters",
        list(by_id),
        index=None,
        format_func=lambda i: _label(by_id[i]),
        placeholder=f"Search {len(by_id)} MLB hitters — e.g. Brice Turang",
        key="scout_search",
        on_change=_on_search,
        args=(by_id,),
        label_visibility="collapsed",
    )

    hand = _render_controls()
    st.markdown(f'<div class="context-line">{_context_line(hand)}</div>', unsafe_allow_html=True)
    _render_recent()

    if not current:
        return
    try:
        with st.spinner(f"Loading {current['name']} from Baseball Savant…"):
            profile = get_profile(current, CURRENT_SEASON, hand)
    except Exception as exc:
        st.error(f"Couldn't load {current['name']}: {exc}")
        return

    arsenal = st.session_state.arsenal if st.session_state.throwing_hand else []
    render_hitter_card(profile, arsenal, st.session_state.analysis_mode, show_metrics=True)
    st.caption(GLOSSARY)


def _render_controls() -> str:
    """Depth control, plus a hand picker when no profile hand is set. Returns 'R'/'L'."""
    depth_col, hand_col = st.columns([3, 2], vertical_alignment="center")
    with depth_col:
        depth = st.segmented_control("Report depth", ANALYSIS_MODES,
                                     default=st.session_state.analysis_mode,
                                     key="scout_depth", label_visibility="collapsed")
        if depth:
            st.session_state.analysis_mode = depth

    if st.session_state.throwing_hand:
        return hand_code(st.session_state.throwing_hand)
    with hand_col:
        picked = st.segmented_control("Facing", ["vs RHP", "vs LHP"], default="vs RHP",
                                      key="scout_hand", label_visibility="collapsed",
                                      help="No throwing hand saved on My Arsenal — pick which side to scout from.")
    return "L" if picked == "vs LHP" else "R"


def _context_line(hand: str) -> str:
    parts = []
    if st.session_state.throwing_hand and st.session_state.arsenal:
        name = html.escape(st.session_state.pitcher_name or "Your arsenal")
        parts.append(f"<b>{name}</b> · {hand}HP · {len(st.session_state.arsenal)} pitches")
    else:
        parts.append(f"No arsenal yet — showing tendencies vs {hand}HP")
    parts.append(f"{CURRENT_SEASON} regular season · Baseball Savant")
    return " &nbsp;·&nbsp; ".join(parts)


def _render_recent() -> None:
    recent = st.session_state.scout_recent
    if not recent:
        return
    current = st.session_state.scout_current
    with st.container(horizontal=True, vertical_alignment="center"):
        for h in recent:
            st.button(h["name"], key=f"recent-{h['id']}", on_click=_select, args=(h,),
                      type="primary" if current and current["id"] == h["id"] else "secondary",
                      icon=":material/history:")
        st.button("Clear", key="recent-clear", on_click=_clear, type="tertiary")
