"""Session-state helpers so UI modules share data without tight coupling."""

from __future__ import annotations

import streamlit as st

from pitchiq.profile_store import PERSISTED_KEYS, load_profile

_DEFAULTS: dict = {
    # Pitcher profile
    "pitcher_name": "",
    "throwing_hand": None,
    # arsenal entries: pitch, velo_low/high/avg, usage_pct, ivb, hb, plus what the
    # pitcher writes (notes = "how I throw it", plan_vs_rhh/lhh, best_counts,
    # confidence) and, for pitches from uploaded reports, season `stats`.
    "arsenal": [],
    "strengths": "",
    "weaknesses": "",
    "preferences": "",
    "approach": "",         # how I attack hitters / pitching identity
    "outings": [],          # extracted pitcher reports (one per uploaded PDF)
    "notes_docs": [],       # other uploads as text: id, filename, text, added
    # Uploads (metadata only in V0.1; bytes kept for future extraction)
    "pitcher_reports": [],  # list[dict]: name, size_kb, status
    "opponent_reports": [],
    # PDF extraction (V0.5)
    "extraction_cache": {},  # cache_key -> extraction result dict (editable)
    "pdf_store": {},         # cache_key -> raw PDF bytes (heatmap rendering)
    # Analysis settings
    "analysis_mode": "Standard",
    # Scout (MLB hitter search)
    "scout_current": None,   # hitter dict currently shown: id, name, position, team, bats, number
    "scout_recent": [],      # recently searched hitter dicts, newest first
    "scout_search": None,    # search box value (cleared after each pick)
    "hitter_profiles": {},   # "id:season:hand" -> computed hitter profile (shared by pages)
    # Team Matchup
    "team_matchup": None,    # last built team plan: team, season, hand, profiles, failed
}


def init_state() -> None:
    """Seed st.session_state with defaults, then the saved profile (once per session)."""
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not st.session_state.get("_profile_loaded"):
        st.session_state.update(load_profile())
        st.session_state._profile_loaded = True


def current_profile() -> dict:
    """The saved-profile fields as a plain dict (for saving and the knowledge base)."""
    return {key: st.session_state.get(key) for key in PERSISTED_KEYS}


def profile_complete() -> bool:
    """A profile is usable once a hand is chosen and at least one pitch exists."""
    return bool(st.session_state.throwing_hand) and len(st.session_state.arsenal) > 0
