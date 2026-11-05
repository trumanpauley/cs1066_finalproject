"""My Arsenal: who you are, your reports, your pitches in your own words.

Everything here is saved automatically (pitchiq/profile_store.py) and turned
into the knowledge base the scouting chatbot will search (pitchiq/knowledge).

Widget pattern: every input has its own widget key ("w_..." / "q_...") that is
seeded from the saved value only when the widget has no state yet. That keeps
typed values when you switch pages (Streamlit drops state for widgets that
aren't on screen) and lets uploads overwrite values by clearing the widget keys.
"""

from __future__ import annotations

import json
from datetime import date

import plotly.graph_objects as go
import streamlit as st

from pitchiq.arsenal import (
    CONFIDENCE_OPTIONS,
    COUNT_OPTIONS,
    combine_outings,
    merge_into_arsenal,
    outing_sort_key,
)
from pitchiq.config import MAX_UPLOAD_MB, MOVEMENT_RANGE, PITCH_COLORS, PITCH_TYPES, THROWING_HANDS
from pitchiq.data.sample_data import DEFAULT_ARSENAL
from pitchiq.extraction import extract_report, extract_text
from pitchiq.knowledge import build_chunks, pitcher_documents
from pitchiq.profile_store import PROFILE_DIR, content_id, delete_upload, save_profile, save_upload
from pitchiq.state import current_profile

UPLOAD_TYPES = ["pdf", "txt", "md"]
OPPONENT_REPORT_TYPES = {"opponent_stats", "opponent_heatmap"}


def render_pitcher_profile() -> None:
    st.markdown("### My Arsenal")
    st.caption(
        "Everything PitchIQ knows about you: your reports, your pitches, and how you "
        "like to use them. Game plans on Scout and Team Matchup are built from this."
    )

    _render_identity()
    _render_reports()
    _render_pitches()
    _render_movement_section()
    _render_self_scouting()
    _render_knowledge_preview()
    _autosave()


# ---------------------------------------------------------------------------
# Widget <-> saved value binding
# ---------------------------------------------------------------------------

def _seed(widget_key: str, value) -> None:
    """Give a widget the saved value, unless it already holds a newer one."""
    if widget_key not in st.session_state:
        st.session_state[widget_key] = value


def _clear_widget_keys(pitch: str | None = None) -> None:
    """Drop per-pitch widget state (one pitch or all) after data changes underneath it."""
    for key in list(st.session_state.keys()):
        if key.startswith(("mv_", "q_")) and (pitch is None or key.endswith(f"::{pitch}")):
            del st.session_state[key]


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def _render_identity() -> None:
    col_name, col_hand = st.columns([2, 1])
    _seed("w_pitcher_name", st.session_state.pitcher_name)
    _seed("w_throwing_hand", st.session_state.throwing_hand)
    with col_name:
        st.session_state.pitcher_name = st.text_input(
            "Pitcher name", key="w_pitcher_name", placeholder="e.g., Truman Pauley")
    with col_hand:
        st.session_state.throwing_hand = st.selectbox(
            "Throwing hand", THROWING_HANDS, key="w_throwing_hand", placeholder="Select...")


# ---------------------------------------------------------------------------
# Reports: upload, list, season summary
# ---------------------------------------------------------------------------

def _render_reports() -> None:
    st.markdown("#### My Reports")
    st.caption(
        "Upload your pitching reports (Sockeye process reports) — every outing is combined "
        "into your season numbers below. Anything else (coach's notes, a bullpen plan, a "
        "PDF or text file) is saved as notes for the scouting assistant."
    )
    nonce = st.session_state.setdefault("upload_nonce", 0)
    files = st.file_uploader("Upload reports or notes", type=UPLOAD_TYPES, accept_multiple_files=True,
                             key=f"arsenal_upload_{nonce}", label_visibility="collapsed")
    if files:
        messages = _process_uploads(files)
        st.session_state.upload_messages = messages
        st.session_state.upload_nonce = nonce + 1  # fresh, empty uploader
        st.rerun()
    for level, msg in st.session_state.pop("upload_messages", []):
        getattr(st, level)(msg)

    outings = sorted(st.session_state.outings, key=outing_sort_key, reverse=True)
    notes = st.session_state.notes_docs
    if not outings and not notes:
        return

    if outings:
        _render_season_summary(outings)
        for o in outings:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 3, 1], vertical_alignment="center")
                c1.markdown(f"**{o.get('date_range') or 'Undated'}**  \n"
                            f"<span style='color:#8b93a3;font-size:0.8rem'>{o['filename']}</span>",
                            unsafe_allow_html=True)
                n = sum(p.get("usage_count") or 0 for p in o["pitches"])
                c2.markdown(f"{n} pitches · {len(o['pitches'])} types")
                c3.markdown(f"Race to 2K {o.get('race_to_2k') or '—'}  \nFPS {o.get('first_pitch_strikes') or '—'}")
                c4.button(":material/delete:", key=f"del_outing_{o['id']}", help="Remove this report",
                          on_click=_delete_outing, args=(o["id"],))
                if o.get("errors"):
                    st.caption("Extraction notes: " + " ".join(o["errors"]))

    for note in notes:
        with st.container(border=True):
            c1, c2 = st.columns([8, 1], vertical_alignment="center")
            c1.markdown(f":material/description: **{note['filename']}** · notes · "
                        f"{len(note['text']):,} characters · added {note['added']}")
            c2.button(":material/delete:", key=f"del_note_{note['id']}", help="Remove these notes",
                      on_click=_delete_note, args=(note["id"],))


def _render_season_summary(outings: list[dict]) -> None:
    s = combine_outings(outings)["summary"]
    cols = st.columns(4)
    cols[0].metric("Outings", s["outings"])
    cols[1].metric("Pitches", s["pitches"])
    for col, key, label in ((cols[2], "race_to_2k", "Race to 2K"),
                            (cols[3], "first_pitch_strikes", "First-pitch strikes")):
        v = s[key]
        if not v["total"]:
            col.metric(label, "—")
            continue
        mlb = float(v["mlb"].rstrip("%")) if v["mlb"] else None
        col.metric(label, f"{v['pct']:.0f}%",
                   delta=f"{v['pct'] - mlb:+.0f} pts vs MLB" if mlb is not None else None,
                   help=f"{v['made']}/{v['total']} across your uploaded outings. "
                        f"Season: {v['season'] or 'n/a'} · MLB average: {v['mlb'] or 'n/a'}.")


def _process_uploads(files: list) -> list[tuple[str, str]]:
    """Extract each file into an outing or a notes doc. Returns (level, message) pairs."""
    messages: list[tuple[str, str]] = []
    known = {o["id"] for o in st.session_state.outings} | {n["id"] for n in st.session_state.notes_docs}
    new_outing = False
    for f in files:
        data = f.getvalue()
        file_id = content_id(data)
        if file_id in known:
            messages.append(("info", f"{f.name} is already uploaded."))
            continue
        if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
            messages.append(("error", f"{f.name} is over the {MAX_UPLOAD_MB} MB limit."))
            continue

        if f.name.lower().endswith(".pdf"):
            result = extract_report(data, f.name)
            if result["report_type"] == "pitcher_report" and result.get("pitches"):
                outing = {k: v for k, v in result.items() if k != "page_count"}
                outing["id"] = file_id
                st.session_state.outings.append(outing)
                new_outing = True
                messages.append(("success", f"{f.name}: outing {result.get('date_range') or ''} — "
                                            f"{len(result['pitches'])} pitch types added."))
            elif result["report_type"] in OPPONENT_REPORT_TYPES:
                messages.append(("warning", f"{f.name} looks like an opponent report. My Arsenal is for "
                                            "your own data — opponent scouting comes from MLB data."))
                continue
            else:
                try:
                    text = extract_text(data)
                except Exception as exc:
                    messages.append(("error", f"{f.name}: couldn't read the PDF ({exc})."))
                    continue
                if not text:
                    messages.append(("error", f"{f.name} has no readable text (a scanned image?)."))
                    continue
                _add_note(file_id, f.name, text)
                messages.append(("success", f"{f.name}: saved as notes ({len(text):,} characters)."))
        else:
            text = data.decode("utf-8", errors="replace").strip()
            if not text:
                messages.append(("error", f"{f.name} is empty."))
                continue
            _add_note(file_id, f.name, text)
            messages.append(("success", f"{f.name}: saved as notes."))

        save_upload(file_id, f.name, data)
        known.add(file_id)

    if new_outing:
        _rebuild_arsenal_from_reports()
        messages.append(("info", "Your pitches below were updated from the reports. "
                                 "Anything you wrote about each pitch was kept."))
    return messages


def _add_note(file_id: str, filename: str, text: str) -> None:
    st.session_state.notes_docs.append({"id": file_id, "filename": filename, "text": text,
                                        "added": date.today().isoformat()})


def _rebuild_arsenal_from_reports() -> None:
    combined = combine_outings(st.session_state.outings)
    st.session_state.arsenal = merge_into_arsenal(st.session_state.arsenal, combined)
    _clear_widget_keys()


def _delete_outing(outing_id: str) -> None:
    st.session_state.outings = [o for o in st.session_state.outings if o["id"] != outing_id]
    delete_upload(outing_id)
    _rebuild_arsenal_from_reports()


def _delete_note(note_id: str) -> None:
    st.session_state.notes_docs = [n for n in st.session_state.notes_docs if n["id"] != note_id]
    delete_upload(note_id)


# ---------------------------------------------------------------------------
# Pitches
# ---------------------------------------------------------------------------

def _render_pitches() -> None:
    st.markdown("#### My Pitches")
    arsenal = st.session_state.arsenal
    if not arsenal:
        st.info("No pitches yet. Upload a pitching report above, add a pitch by hand, "
                "or load the example arsenal.")
    for i, p in enumerate(arsenal):
        _render_pitch_card(i, p)

    if arsenal:
        total = sum(p.get("usage_pct") or 0 for p in arsenal)
        if abs(total - 100) > 2:
            st.caption(f"Usage adds up to {total}% — aim for 100%.")
    _render_add_pitch()


def _render_pitch_card(index: int, p: dict) -> None:
    pitch = p["pitch"]
    color = PITCH_COLORS.get(pitch, "#9fb6c9")
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1], vertical_alignment="center")
        c1.markdown(f'<span style="color:{color};font-size:1.1rem;">●</span> **{pitch}**',
                    unsafe_allow_html=True)
        avg = f" ({p['velo_avg']:.0f})" if p.get("velo_avg") else ""
        c2.markdown(f"{p.get('velo_low')}–{p.get('velo_high')}{avg} mph")
        c3.markdown(f"{p.get('usage_pct', 0)}% usage")
        c4.button(":material/delete:", key=f"del_pitch_{index}", help=f"Remove {pitch}",
                  on_click=_delete_pitch, args=(index,))

        s = p.get("stats")
        if s:
            st.caption(
                f"{s['pitches']} pitches in {s['outings']} outing(s) · "
                f"Whiff {_pct(s['whiff_pct'])} · Strike {_pct(s['strike_pct'])} · "
                f"First-pitch strike {_pct(s['fpk_pct'])} · "
                f"Share vs LHH {_pct(s['usage_vl'])} / RHH {_pct(s['usage_vr'])} · "
                f"With 2 strikes vs LHH {_pct(s['usage_2k_vl'])} / RHH {_pct(s['usage_2k_vr'])}"
            )

        with st.expander("How I use it"):
            _pitch_text(p, "notes", "How I throw it",
                        "Grip, feel, intent, shape — e.g. 'Sweeper: start it at the hip of a righty and "
                        "let it sweep off the plate. Throw it harder when I'm ahead.'", height=90)
            left, right = st.columns(2)
            with left:
                _pitch_text(p, "plan_vs_rhh", "Plan vs right-handed hitters",
                            "Where and when vs RHH", height=80)
            with right:
                _pitch_text(p, "plan_vs_lhh", "Plan vs left-handed hitters",
                            "Where and when vs LHH", height=80)
            left, right = st.columns([3, 2])
            key = f"q_best_counts::{pitch}"
            _seed(key, p.get("best_counts") or [])
            p["best_counts"] = left.multiselect("Go-to counts", COUNT_OPTIONS, key=key)
            key = f"q_confidence::{pitch}"
            _seed(key, p.get("confidence"))
            p["confidence"] = right.selectbox("Confidence", CONFIDENCE_OPTIONS, key=key,
                                              placeholder="How much do you trust it?")


def _pitch_text(p: dict, field: str, label: str, placeholder: str, height: int) -> None:
    key = f"q_{field}::{p['pitch']}"
    _seed(key, p.get(field) or "")
    p[field] = st.text_area(label, key=key, placeholder=placeholder, height=height)


def _pct(v) -> str:
    return "—" if v is None else f"{v:.0f}%"


def _delete_pitch(index: int) -> None:
    removed = st.session_state.arsenal.pop(index)
    _clear_widget_keys(removed["pitch"])


def _render_add_pitch() -> None:
    with st.expander("Add a pitch by hand"):
        with st.form("add_pitch_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            pitch = c1.selectbox("Pitch type", PITCH_TYPES)
            usage = c2.number_input("Usage %", min_value=0, max_value=100, value=20)
            velo_low, velo_high = st.slider("Velocity range (mph)", 55, 105, (84, 88))
            mv1, mv2 = st.columns(2)
            ivb = mv1.number_input("IVB (in.)", min_value=-MOVEMENT_RANGE, max_value=MOVEMENT_RANGE,
                                   value=0.0, step=0.1,
                                   help="Induced vertical break — positive = ride, negative = drop.")
            hb = mv2.number_input("HB (in.)", min_value=-MOVEMENT_RANGE, max_value=MOVEMENT_RANGE,
                                  value=0.0, step=0.1,
                                  help="Horizontal break — positive = arm side, negative = glove side (RHP view).")
            submitted = st.form_submit_button("Add pitch", width="stretch")
        if submitted:
            if pitch in {p["pitch"] for p in st.session_state.arsenal}:
                st.warning(f"{pitch} is already in your arsenal — remove it first to re-add.")
            else:
                st.session_state.arsenal.append({
                    "pitch": pitch, "velo_low": velo_low, "velo_high": velo_high,
                    "usage_pct": usage, "ivb": ivb, "hb": hb, "notes": "", "source": "manual",
                })
                st.rerun()

        if st.button("Load example arsenal", help="Replaces your pitches with a sample four-pitch mix."):
            _clear_widget_keys()
            st.session_state.arsenal = [dict(p) for p in DEFAULT_ARSENAL]
            st.rerun()


# ---------------------------------------------------------------------------
# Self-scouting
# ---------------------------------------------------------------------------

_SELF_SCOUTING = (
    ("strengths", "Strengths", "e.g., Sweeper gets whiffs vs RHH; I win the race to two strikes."),
    ("weaknesses", "Weaknesses", "e.g., Fastball command glove-side; first-pitch strikes are below average."),
    ("preferences", "Preferences", "e.g., Like to pitch backwards when ahead; want ground balls with runners on."),
    ("approach", "How I attack hitters",
     "Your pitching identity in a few sentences — what you lean on, how you sequence, "
     "what you do when you're behind."),
)


def _render_self_scouting() -> None:
    st.markdown("#### Self-Scouting")
    cols = st.columns(2)
    for i, (field, label, placeholder) in enumerate(_SELF_SCOUTING):
        key = f"w_{field}"
        _seed(key, st.session_state[field])
        with cols[i % 2]:
            st.session_state[field] = st.text_area(label, key=key, height=120, placeholder=placeholder)


# ---------------------------------------------------------------------------
# Knowledge base preview (what the RAG chatbot will search)
# ---------------------------------------------------------------------------

def _render_knowledge_preview() -> None:
    docs = pitcher_documents(current_profile())
    chunks = build_chunks(docs)
    with st.expander(f"What PitchIQ knows about you · {len(docs)} documents, {len(chunks)} chunks"):
        st.caption(
            "This is your side of the knowledge base the scouting chatbot will search: one "
            "document for your overview, each pitch, each outing, and each notes file. "
            "MLB hitter data gets the same treatment. Long documents are split into chunks "
            "so the right piece can be retrieved."
        )
        for doc in docs:
            st.markdown(f"**{doc.title}** · `{doc.kind}`")
            st.code(doc.text, language=None, wrap_lines=True)


def _autosave() -> None:
    profile = current_profile()
    blob = json.dumps(profile, sort_keys=True, default=str)
    if blob != st.session_state.get("_saved_blob"):
        save_profile(profile)
        st.session_state._saved_blob = blob
    st.caption(f"Saved automatically to `{PROFILE_DIR.name}/profile.json` on this computer.")


# ---------------------------------------------------------------------------
# Pitch movement chart (HB vs. IVB) with synchronized numeric inputs
# ---------------------------------------------------------------------------

def _movement_key(kind: str, pitch: str) -> str:
    return f"mv_{kind}::{pitch}"


def _render_movement_section() -> None:
    st.markdown("#### Pitch Movement Profile")
    if not st.session_state.arsenal:
        st.caption("Add pitches above to plot their movement (HB vs. IVB).")
        return

    st.caption(
        "Movement from the catcher's view, like your pitching report: HB (horizontal "
        "break) on the x-axis, IVB (induced vertical break) on the y-axis. Adjust the "
        "numbers and the chart updates instantly."
    )

    chart_col, edit_col = st.columns([3, 2])

    # Inputs first so the chart reflects this rerun's edits immediately.
    with edit_col:
        st.markdown("**Adjust movement (inches)**")
        for p in st.session_state.arsenal:
            color = PITCH_COLORS.get(p["pitch"], "#9fb6c9")
            st.markdown(
                f'<span style="color:{color};">●</span> **{p["pitch"]}**',
                unsafe_allow_html=True,
            )
            c_hb, c_ivb = st.columns(2)
            for col, kind, label in ((c_hb, "hb", "HB"), (c_ivb, "ivb", "IVB")):
                key = _movement_key(kind, p["pitch"])
                _seed(key, float(p.get(kind) or 0.0))
                p[kind] = col.number_input(label, min_value=-MOVEMENT_RANGE, max_value=MOVEMENT_RANGE,
                                           step=0.5, key=key)

    with chart_col:
        st.plotly_chart(
            _build_movement_figure(st.session_state.arsenal),
            width="stretch",
            config={"displayModeBar": False},
        )


def _build_movement_figure(arsenal: list[dict]) -> go.Figure:
    fig = go.Figure()

    for p in arsenal:
        color = PITCH_COLORS.get(p["pitch"], "#9fb6c9")
        usage = max(p.get("usage_pct") or 10, 5)
        fig.add_trace(
            go.Scatter(
                x=[p.get("hb", 0.0)],
                y=[p.get("ivb", 0.0)],
                mode="markers+text",
                name=p["pitch"],
                text=[p["pitch"].split(" ")[0]],
                textposition="top center",
                textfont=dict(color="#e8f1f9", size=12),
                marker=dict(
                    size=18 + usage * 0.35,  # usage scales marker size
                    color=color,
                    line=dict(color="#0d1b2a", width=2),
                    opacity=0.92,
                ),
                hovertemplate=(
                    f"<b>{p['pitch']}</b><br>"
                    "HB: %{x:.1f} in.<br>IVB: %{y:.1f} in."
                    f"<br>Velo: {p.get('velo_low', '?')}–{p.get('velo_high', '?')} mph"
                    f"<br>Usage: {p.get('usage_pct', 0)}%<extra></extra>"
                ),
            )
        )

    r = MOVEMENT_RANGE
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17, 49, 77, 0.45)",
        height=430,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(
            title="Horizontal Break — HB (in.)",
            range=[-r, r], zeroline=True, zerolinecolor="#4a6b8c", zerolinewidth=2,
            gridcolor="#223c57", dtick=5,
        ),
        yaxis=dict(
            title="Induced Vertical Break — IVB (in.)",
            range=[-r, r], zeroline=True, zerolinecolor="#4a6b8c", zerolinewidth=2,
            gridcolor="#223c57", dtick=5, scaleanchor="x", scaleratio=1,
        ),
    )
    # Quadrant hints (catcher's view).
    fig.add_annotation(x=r * 0.97, y=r * 0.97, text="Arm-side ride", showarrow=False,
                       font=dict(color="#6f8ba6", size=11), xanchor="right")
    fig.add_annotation(x=-r * 0.97, y=-r * 0.97, text="Glove-side sweep/drop", showarrow=False,
                       font=dict(color="#6f8ba6", size=11), xanchor="left")
    return fig
