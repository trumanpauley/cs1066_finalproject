"""Ask PitchIQ: the scouting chatbot (retrieval + Claude or Gemini).

e.g. "How should I pitch to the Dodgers?" -> finds the Dodgers, pulls each
hitter's Savant data, and streams a game plan built around your arsenal.
"""

from __future__ import annotations

import html
import os

import streamlit as st

from pitchiq.assistant import retrieve, system_text, user_turn
from pitchiq.backends import available_backend, error_message
from pitchiq.config import ANALYSIS_MODES
from pitchiq.knowledge import hitter_document, pitcher_documents
from pitchiq.mlb import sources
from pitchiq.mlb.game_plan import build_game_plan
from pitchiq.mlb.hitter_profile import hand_code
from pitchiq.state import current_profile
from pitchiq.ui.hitter_card import CURRENT_SEASON, get_profile

EXAMPLES = [
    "How should I pitch to the Dodgers?",
    "Give me a plan for Aaron Judge.",
    "Which Brewers hitters chase the most with two strikes?",
]


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _teams(season: int) -> list[dict]:
    return sources.list_teams(season)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _hitters(season: int) -> list[dict]:
    return sources.list_hitters(season)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _roster(team_id: int, season: int) -> list[dict]:
    return sources.team_hitters(team_id, season)


def _secret(name: str) -> str | None:
    """API key from the environment or .streamlit/secrets.toml."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        return st.secrets.get(name)
    except Exception:  # no secrets.toml
        return None


def _backend():
    """The chat backend for this conversation (created on first use, reset by New conversation)."""
    if st.session_state.get("chat_backend") is None:
        st.session_state.chat_backend = available_backend(_secret("ANTHROPIC_API_KEY"), _secret("GEMINI_API_KEY"))
    return st.session_state.chat_backend


def render_chat() -> None:
    log = st.session_state.chat_log
    if not log:
        st.markdown(
            '<div class="scout-hero"><h1>Ask PitchIQ</h1>'
            "<p>Game plans against any MLB team or hitter, built from your arsenal.</p></div>",
            unsafe_allow_html=True,
        )
    for entry in log:
        _render_entry(entry)

    backend = _backend()
    ready = _render_setup_notes(backend)
    _render_controls(backend)

    if not log and ready:
        with st.container(horizontal=True):
            for i, example in enumerate(EXAMPLES):
                if st.button(example, key=f"example-{i}", type="secondary"):
                    st.session_state.chat_pending = example
                    st.rerun()

    question = st.chat_input("Ask about a team or hitter — e.g. How should I pitch to the Dodgers?",
                             disabled=not ready)
    question = question or st.session_state.pop("chat_pending", None)
    if question and ready:
        _answer(backend, question.strip())


def _render_setup_notes(backend) -> bool:
    """Explain what's missing (API key, throwing hand). Returns True when chat can run."""
    ok = True
    if backend is None:
        st.info(
            "**Add an API key to turn on the chatbot.** Create `.streamlit/secrets.toml` with "
            "`GEMINI_API_KEY = \"...\"` (free key from aistudio.google.com) or "
            "`ANTHROPIC_API_KEY = \"sk-ant-...\"` (console.anthropic.com), then restart the app. "
            "The file is git-ignored."
        )
        ok = False
    elif backend.provider == "gemini":
        st.caption(":material/info: Gemini's free tier may use what you send to improve Google's "
                   "products — test with the fictional files in `samples/`, not team reports.")
    if not st.session_state.throwing_hand:
        st.info("Set your throwing hand on **My Arsenal** — hitter data is pulled against your hand.")
        ok = False
    elif not st.session_state.arsenal:
        st.caption("No pitches on **My Arsenal** yet — answers will be about hitters only, not a plan for you.")
    return ok


def _render_controls(backend) -> None:
    left, right = st.columns([3, 1], vertical_alignment="center")
    with left:
        depth = st.segmented_control("Report depth", ANALYSIS_MODES, default=st.session_state.analysis_mode,
                                     key="chat_depth", label_visibility="collapsed")
        if depth:
            st.session_state.analysis_mode = depth
    with right:
        if st.session_state.chat_log and st.button("New conversation", type="tertiary"):
            st.session_state.chat_log, st.session_state.chat_sent_ids = [], []
            st.session_state.chat_backend = None
            st.rerun()

    name = html.escape(st.session_state.pitcher_name or "Your profile")
    n = len(st.session_state.arsenal)
    hand = hand_code(st.session_state.throwing_hand) + "HP" if st.session_state.throwing_hand else "no hand set"
    notes = len(st.session_state.notes_docs)
    model = backend.label if backend else "no model connected"
    st.markdown(
        f'<div class="context-line"><b>{name}</b> · {hand} · {n} pitches'
        f'{f" · {notes} notes file" + ("s" if notes != 1 else "") if notes else ""}'
        f" &nbsp;·&nbsp; {CURRENT_SEASON} Baseball Savant &nbsp;·&nbsp; {html.escape(model)}</div>",
        unsafe_allow_html=True,
    )


def _render_entry(entry: dict) -> None:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry["role"] == "assistant":
            _render_meta(entry)


def _render_meta(entry: dict) -> None:
    bits = [entry.get("depth", ""), entry.get("model", "")]
    if entry.get("cost") is not None:
        bits.append("free" if entry["cost"] == 0 else f"≈ ${entry['cost']:.3f}")
    if entry.get("tokens"):
        bits.append(f"{entry['tokens']:,} tokens")
    if entry.get("note"):
        bits.append(entry["note"])
    st.caption(" · ".join(b for b in bits if b))
    sources_ = entry.get("sources") or []
    if sources_:
        with st.expander(f"Sources · {len(sources_)} documents"):
            st.markdown("\n".join(f"- {html.escape(s)}" for s in sources_))
            st.caption("Plus your profile: overview, each pitch, and each outing report.")


def _answer(backend, question: str) -> None:
    hand = hand_code(st.session_state.throwing_hand)
    arsenal = st.session_state.arsenal
    depth = st.session_state.analysis_mode
    st.session_state.chat_log.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    def roster_for(team: dict) -> list[dict]:
        return [{**h, "team": team["abbreviation"]} for h in _roster(team["id"], CURRENT_SEASON)]

    def hitter_doc_for(hitter: dict):
        profile = get_profile(hitter, CURRENT_SEASON, hand)
        return hitter_document(profile, build_game_plan(profile, arsenal), CURRENT_SEASON)

    profile_docs = pitcher_documents(current_profile())
    note_docs = [d for d in profile_docs if d.kind == "note"]
    sent = st.session_state.chat_sent_ids
    with st.status("Finding the data for your question…", expanded=False) as status:
        ctx = retrieve(question, teams=_teams(CURRENT_SEASON), hitters=_hitters(CURRENT_SEASON),
                       roster_for=roster_for, hitter_doc_for=hitter_doc_for, note_docs=note_docs,
                       already_sent=set(sent),
                       recent_hitter_ids={int(i.split(":")[1]) for i in sent if i.startswith("hitter:")})
        found = [t["name"] for t in ctx.teams]
        if ctx.hitters:
            n = len(ctx.hitters)
            found.append(", ".join(h["name"] for h in ctx.hitters) if n <= 3 else f"{n} hitters")
        status.update(label="Using " + (", ".join(found) if found else "your profile and earlier messages"),
                      state="complete")

    entry = {"role": "assistant", "content": "", "depth": depth, "model": backend.label,
             "sources": ctx.source_titles()}
    with st.chat_message("assistant"):
        waiting = st.empty()
        waiting.caption("Thinking through the matchups… a full-team report usually takes 15–45 seconds.")

        def text():
            first = True
            for chunk in backend.stream(system_text([d for d in profile_docs if d.kind != "note"]),
                                        user_turn(question, ctx, depth)):
                if first:
                    waiting.empty()
                    first = False
                yield chunk

        try:
            entry["content"] = st.write_stream(text()) or ""
        except Exception as exc:
            st.session_state.chat_log.pop()
            st.error(error_message(exc))
            return
        finally:
            waiting.empty()  # never leave "Thinking…" on screen

        result = backend.result
        if result.status == "refused":
            st.session_state.chat_log.pop()
            st.warning("The model declined or couldn't finish this request. Try rephrasing it as a scouting question.")
            return
        if result.status == "empty" or not entry["content"].strip():
            st.session_state.chat_log.pop()
            st.warning("The model finished without writing an answer, even after retrying (this happens "
                       "occasionally on the free Gemini models). Please ask again.")
            return
        if result.status == "truncated":
            entry["note"] = "answer may be cut off — ask again for the rest"
        entry["cost"], entry["tokens"] = result.cost, result.tokens
        sent += [d.id for d in ctx.hitter_docs] + [c.id for c in ctx.note_chunks]
        st.session_state.chat_log.append(entry)
        _render_meta(entry)
