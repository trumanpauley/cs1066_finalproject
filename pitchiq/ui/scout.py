"""Scout workspace — the PitchIQ homepage.

A minimal, ChatGPT-style interface: a centered prompt, a composer with
analysis depth and optional file attachments, and conversational scouting
reports. Responses are clearly-labeled demos; the service interface already
threads the pitcher profile, uploads, and attachments through as context so
RAG + LLM answers can slot in later without UI changes.
"""

from __future__ import annotations

import streamlit as st

from pitchiq.config import ANALYSIS_MODES
from pitchiq.services.pdf_service import summarize_upload, validate_upload
from pitchiq.services.report_service import answer_scouting_question
from pitchiq.state import profile_complete


def render_scout() -> None:
    history = st.session_state.chat_history

    if not history:
        st.markdown(
            '<div class="scout-hero">'
            "<h1>What&rsquo;s your game plan?</h1>"
            "<p>Ask about any hitter. Build a plan around your arsenal.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        for msg in history:
            _render_message(msg)

    _render_composer()


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------

def _render_composer() -> None:
    depth_col, clear_col = st.columns([5, 1], vertical_alignment="center")
    with depth_col:
        depth = st.segmented_control(
            "Analysis depth",
            ANALYSIS_MODES,
            default=st.session_state.analysis_mode,
            key="scout_depth",
            label_visibility="collapsed",
        )
        if depth:
            st.session_state.analysis_mode = depth
    with clear_col:
        if st.session_state.chat_history:
            if st.button("Clear chat", type="tertiary"):
                st.session_state.chat_history = []
                st.rerun()

    st.markdown(
        f'<div class="context-line">{_context_line()}</div>',
        unsafe_allow_html=True,
    )

    submission = st.chat_input(
        "I throw a four-seam, slider, and changeup. How should I pitch to ...",
        accept_file="multiple",
        file_type=["pdf"],
    )

    if submission:
        if isinstance(submission, str):
            text, files = submission, []
        else:
            text = submission.text or ""
            files = list(submission.files or [])

        _store_attachments(files)
        if text.strip():
            _process_question(text.strip(), st.session_state.analysis_mode)
        st.rerun()


def _context_line() -> str:
    parts: list[str] = []
    if profile_complete():
        name = st.session_state.pitcher_name or "Your profile"
        parts.append(f"<b>{name}</b> · {len(st.session_state.arsenal)} pitches")
    else:
        parts.append("No profile — optional, add one in My Arsenal")

    n_reports = len(st.session_state.pitcher_reports) + len(
        st.session_state.opponent_reports
    )
    if n_reports:
        parts.append(f"{n_reports} report{'s' if n_reports != 1 else ''} in library")
    if st.session_state.chat_attachments:
        names = ", ".join(a["name"] for a in st.session_state.chat_attachments)
        parts.append(f"Attached: {names}")
    parts.append("Demo data")
    return " &nbsp;·&nbsp; ".join(parts)


def _store_attachments(files: list) -> None:
    for f in files:
        ok, message = validate_upload(f)
        if not ok:
            st.error(f"{f.name} — {message}")
            continue
        existing = {a["name"] for a in st.session_state.chat_attachments}
        if f.name not in existing:
            st.session_state.chat_attachments.append(summarize_upload(f))


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def _render_message(msg: dict) -> None:
    if msg["role"] == "user":
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(msg["content"])
        return

    with st.chat_message("assistant", avatar=":material/sports_baseball:"):
        st.markdown(
            f'<span class="depth-tag">{msg["depth"]}</span>'
            '<span class="demo-tag">Demo response</span>',
            unsafe_allow_html=True,
        )
        st.markdown(msg["content"])

        with st.expander("Evidence and statistics"):
            if msg.get("evidence"):
                for h in msg["evidence"]:
                    st.caption(f"#{h['number']} {h['name']} — pitch-type splits (sample)")
                    st.dataframe(h["stats"], width="stretch", hide_index=True)
            else:
                st.caption("No report data on file for this hitter.")
            st.caption(
                "Zone heatmaps, pitch-level statistics, and source citations will "
                "appear here once report extraction and AI generation land."
            )

        if msg.get("context"):
            with st.expander("Context used"):
                for item in msg["context"]:
                    st.markdown(f"- {item}")


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
        attachments=st.session_state.chat_attachments,
    )
    st.session_state.chat_history.append({"role": "user", "content": question})
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "depth": result["depth"],
            "context": result["context_used"],
            "evidence": result["evidence"],
        }
    )
