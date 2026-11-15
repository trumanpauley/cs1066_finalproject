"""Pitch Simulator page — embeds the React/TypeScript simulator.

The simulator lives in `simulator/` (Vite + React + TypeScript) and is
compiled into one self-contained HTML file, `pitchiq/static/simulator.html`,
so running the Streamlit app never requires Node. Rebuild after changing the
simulator:

    cd simulator && npm install && npm run build

The simulation runs entirely in the browser — no server round-trips or LLM
calls per pitch.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_BUILD = Path(__file__).resolve().parent.parent / "static" / "simulator.html"
_HEIGHT = 1000


@st.cache_data(show_spinner=False)
def _load_build(mtime: float) -> str:
    # mtime is part of the cache key so a rebuild is picked up immediately.
    return _BUILD.read_text(encoding="utf-8")


def render_simulator() -> None:
    st.markdown("### Pitch Simulator")
    st.caption(
        "Pick a pitch, click where to aim, and throw. Outcomes come from a "
        "probability model of the hitter's tendencies — the hitters here are "
        "synthetic demo profiles, not real MLB data."
    )

    if not _BUILD.exists():
        st.warning(
            "The simulator hasn't been built yet. Run "
            "`cd simulator && npm install && npm run build`, then refresh."
        )
        return

    components.html(_load_build(_BUILD.stat().st_mtime), height=_HEIGHT, scrolling=True)
