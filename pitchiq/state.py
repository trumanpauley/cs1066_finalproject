"""Session-state helpers so UI modules share data without tight coupling."""

from __future__ import annotations

import streamlit as st

_DEFAULTS: dict = {
    # Pitcher profile
    "pitcher_name": "",
    "throwing_hand": None,
    "arsenal": [],          # list[dict]: pitch, velo_low, velo_high, usage_pct, notes
    "strengths": "",
    "weaknesses": "",
    "preferences": "",
    "profile_saved": False,
    # Uploads (metadata only in V0.1; bytes kept for future extraction)
    "pitcher_reports": [],  # list[dict]: name, size_kb, status
    "opponent_reports": [],
    # Analysis settings
    "analysis_mode": "Standard",
    # Scout workspace (chat)
    "chat_history": [],     # list[dict]: role, content, depth?, context?
    "pending_prompt": None, # set by quick-prompt buttons
}


def init_state() -> None:
    """Seed st.session_state with defaults (runs once per session)."""
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def profile_complete() -> bool:
    """A profile is usable once a hand is chosen and at least one pitch exists."""
    return bool(st.session_state.throwing_hand) and len(st.session_state.arsenal) > 0
