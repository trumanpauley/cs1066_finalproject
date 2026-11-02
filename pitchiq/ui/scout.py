"""Scout workspace — the PitchIQ homepage.

A ChatGPT-style interface for asking scouting questions and generating game
plans. V0.3 uses a placeholder answer engine over sample data; the layout and
service interface are designed so RAG + LLM answers slot in later without
UI changes (uploaded reports and the pitcher profile are already threaded
through as answer context).
"""

from __future__ import annotations

import streamlit as st

from pitchiq.config import ANALYSIS_MODE_DESCRIPTIONS, ANALYSIS_MODES
from pitchiq.services.report_service import answer_scouting_question
from pitchiq.state import profile_complete

_QUICK_PROMPTS = [
    "Generate a full game plan for this lineup",
    "What are my two-strike putaway options?",
    "How do I attack their highest-threat hitter?",
]


def render_scout() -> None:
    st.markdown("### 🎯 Scouting Workspace")
    st.caption(
        "Ask scouting questions and generate game plans. Answers use the context "
        "shown below — your profile and uploaded reports will ground AI responses "
        "in future versions."
    )

    _render_context_bar()

    # --- Depth selector (applies to the next generated report) --------------
    sel_col, desc_col = st.columns([1, 2])
    with sel_col:
        depth = st.segmented_control(
            "Analysis depth",
            ANALYSIS_MODES,
            default=st.session_state.analysis_mode,
            key="scout_depth",
            help="Sets how detailed the next generated report will be.",
        )
    if depth:
        st.session_state.analysis_mode = depth
    depth = st.session_state.analysis_mode
    with desc_col:
        st.markdown(
            f'<p class="depth-tag" style="margin-top:2.1rem;">{depth}</p> '
            f'<span style="color:#9fb6c9;font-size:0.86rem;">'
            f"{ANALYSIS_MODE_DESCRIPTIONS[depth]}</span>",
            unsafe_allow_html=True,
        )

    # --- Quick prompts -------------------------------------------------------
    if not st.session_state.chat_history:
        st.markdown("**Try one of these to get started:**")
        cols = st.columns(len(_QUICK_PROMPTS))
        for col, prompt in zip(cols, _QUICK_PROMPTS):
            if col.button(prompt, key=f"qp_{prompt[:20]}", width="stretch"):
                st.session_state.pending_prompt = prompt
                st.rerun()

    # --- Chat history + input ------------------------------------------------
    history_box = st.container()

    question = st.chat_input("Ask a scouting question — e.g., “How do I pitch to Dax Carver?”")
    if not question and st.session_state.pending_prompt:
        question = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

    if question:
        _process_question(question, depth)

    with history_box:
        if not st.session_state.chat_history:
            st.info(
                "💬 No reports generated yet. Ask a question below, or use a "
                "quick prompt to generate your first game plan."
            )
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🧢" if msg["role"] == "user" else "⚾"):
                if msg["role"] == "assistant":
                    st.markdown(
                        f'<span class="depth-tag">{msg["depth"]} report</span>',
                        unsafe_allow_html=True,
                    )
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("context"):
                    with st.expander("📂 Context used for this report"):
                        for item in msg["context"]:
                            st.markdown(f"- {item}")

        if st.session_state.chat_history:
            if st.button("🗑️ Clear conversation"):
                st.session_state.chat_history = []
                st.rerun()


def _render_context_bar() -> None:
    """Chips showing which profile and reports feed the answer engine."""
    chips: list[str] = []

    if profile_complete():
        name = st.session_state.pitcher_name or "Unnamed pitcher"
        hand = st.session_state.throwing_hand
        n = len(st.session_state.arsenal)
        chips.append(f'<span class="context-chip">🧢 {name} · {hand} · {n} pitches</span>')
    else:
        chips.append(
            '<span class="context-chip warn">🧢 No pitcher profile — set one up in My Arsenal</span>'
        )

    if st.session_state.pitcher_reports:
        for r in st.session_state.pitcher_reports:
            chips.append(f'<span class="context-chip">🧾 {r["name"]}</span>')
    else:
        chips.append('<span class="context-chip warn">🧾 No pitching report uploaded</span>')

    if st.session_state.opponent_reports:
        for r in st.session_state.opponent_reports:
            chips.append(f'<span class="context-chip">🎯 {r["name"]}</span>')
    else:
        chips.append('<span class="context-chip">🎯 Sample lineup (fictional)</span>')

    st.markdown(
        '<div style="margin:0.2rem 0 0.6rem 0;">'
        '<span style="color:#9fb6c9;font-size:0.8rem;font-weight:700;'
        'letter-spacing:1px;text-transform:uppercase;">Scouting context</span><br>'
        + "".join(chips)
        + "</div>",
        unsafe_allow_html=True,
    )


def _process_question(question: str, depth: str) -> None:
    profile = {
        "pitcher_name": st.session_state.pitcher_name,
        "throwing_hand": st.session_state.throwing_hand,
        "arsenal": st.session_state.arsenal,
        "strengths": st.session_state.strengths,
        "weaknesses": st.session_state.weaknesses,
        "preferences": st.session_state.preferences,
    }
    result = answer_scouting_question(
        question,
        profile,
        depth,
        pitcher_reports=st.session_state.pitcher_reports,
        opponent_reports=st.session_state.opponent_reports,
    )
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "depth": result["depth"],
            "context": result["context_used"],
        }
    )
