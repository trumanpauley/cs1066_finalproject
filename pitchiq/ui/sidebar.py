"""Sidebar: branding, analysis-mode control, and session status."""

from __future__ import annotations

import streamlit as st

from pitchiq.config import (
    ANALYSIS_MODE_DESCRIPTIONS,
    ANALYSIS_MODES,
    APP_ICON,
    APP_NAME,
    VERSION,
)
from pitchiq.state import profile_complete


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(f"## {APP_ICON} {APP_NAME}")
        st.caption(f"Version {VERSION} — UI Foundation")
        st.divider()

        st.markdown("### 🎚️ Analysis Depth")
        st.radio(
            "Choose report depth",
            ANALYSIS_MODES,
            key="analysis_mode",
            help="Controls how much detail appears in the scouting report.",
        )
        st.info(ANALYSIS_MODE_DESCRIPTIONS[st.session_state.analysis_mode])

        st.divider()
        st.markdown("### 📋 Session Status")
        _status_row("Pitcher profile", profile_complete())
        _status_row("My report uploaded", len(st.session_state.pitcher_reports) > 0)
        _status_row("Opponent report uploaded", len(st.session_state.opponent_reports) > 0)

        st.divider()
        st.caption(
            "🔮 Coming in future versions: PDF data extraction, "
            "AI-generated reports, and opponent databases."
        )


def _status_row(label: str, done: bool) -> None:
    icon = "✅" if done else "⬜"
    st.markdown(f"{icon} {label}")
