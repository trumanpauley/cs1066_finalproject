"""Pitcher Profile section: hand, arsenal, movement chart, self-scouting."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from pitchiq.config import MOVEMENT_RANGE, PITCH_COLORS, PITCH_TYPES, THROWING_HANDS
from pitchiq.data.sample_data import DEFAULT_ARSENAL


def render_pitcher_profile() -> None:
    st.markdown("### 🧢 My Arsenal")
    st.caption(
        "Tell PitchIQ about yourself. Your profile and arsenal provide the context "
        "the Scout workspace uses to personalize game plans."
    )

    # --- Identity -----------------------------------------------------------
    col_name, col_hand = st.columns([2, 1])
    with col_name:
        st.text_input("Pitcher name", key="pitcher_name", placeholder="e.g., Truman Pauley")
    with col_hand:
        st.selectbox(
            "Throwing hand",
            THROWING_HANDS,
            key="throwing_hand",
            index=None,
            placeholder="Select...",
        )

    # --- Pitch arsenal ------------------------------------------------------
    st.markdown("#### Build Your Arsenal")
    arsenal_col, add_col = st.columns([3, 2])

    with add_col:
        with st.form("add_pitch_form", clear_on_submit=True):
            st.markdown("**Add a pitch**")
            pitch = st.selectbox("Pitch type", PITCH_TYPES)
            velo_low, velo_high = st.slider(
                "Velocity range (mph)", 55, 105, (84, 88)
            )
            usage = st.number_input("Usage %", min_value=0, max_value=100, value=20)
            mv1, mv2 = st.columns(2)
            ivb = mv1.number_input(
                "IVB (in.)", min_value=-MOVEMENT_RANGE, max_value=MOVEMENT_RANGE,
                value=0.0, step=0.1,
                help="Induced vertical break — positive = ride, negative = drop.",
            )
            hb = mv2.number_input(
                "HB (in.)", min_value=-MOVEMENT_RANGE, max_value=MOVEMENT_RANGE,
                value=0.0, step=0.1,
                help="Horizontal break — positive = arm side, negative = glove side (RHP view).",
            )
            notes = st.text_input("Notes (movement, feel, when you use it)")
            submitted = st.form_submit_button("➕ Add pitch", width="stretch")

        if submitted:
            existing = [p["pitch"] for p in st.session_state.arsenal]
            if pitch in existing:
                st.warning(f"{pitch} is already in your arsenal — remove it first to re-add.")
            else:
                st.session_state.arsenal.append(
                    {
                        "pitch": pitch,
                        "velo_low": velo_low,
                        "velo_high": velo_high,
                        "usage_pct": usage,
                        "ivb": ivb,
                        "hb": hb,
                        "notes": notes,
                    }
                )
                st.rerun()

        if st.button("⚡ Load example arsenal", width="stretch",
                     help="Pre-fills a sample four-pitch mix you can edit."):
            _clear_movement_keys()
            st.session_state.arsenal = [dict(p) for p in DEFAULT_ARSENAL]
            st.rerun()

    with arsenal_col:
        if not st.session_state.arsenal:
            st.info("No pitches yet. Add your pitches on the right, or load the example arsenal.")
        else:
            total_usage = sum(p["usage_pct"] for p in st.session_state.arsenal)
            for i, p in enumerate(st.session_state.arsenal):
                row = st.container(border=True)
                with row:
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    color = PITCH_COLORS.get(p["pitch"], "#9fb6c9")
                    c1.markdown(
                        f'<span style="color:{color};font-size:1.1rem;">●</span> '
                        f"**{p['pitch']}**",
                        unsafe_allow_html=True,
                    )
                    c2.markdown(f"{p['velo_low']}–{p['velo_high']} mph")
                    c3.markdown(f"{p['usage_pct']}% usage")
                    if c4.button("🗑️", key=f"del_pitch_{i}", help=f"Remove {p['pitch']}"):
                        removed = st.session_state.arsenal.pop(i)
                        _clear_movement_keys(removed["pitch"])
                        st.rerun()
                    if p["notes"]:
                        st.caption(p["notes"])
            if total_usage != 100:
                st.caption(f"⚠️ Usage adds up to {total_usage}% (aim for 100%).")
            else:
                st.caption("✅ Usage adds up to 100%.")

    # --- Pitch movement chart ------------------------------------------------
    _render_movement_section()

    # --- Self-scouting ------------------------------------------------------
    st.markdown("#### Self-Scouting")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_area(
            "💪 Strengths", key="strengths", height=130,
            placeholder="e.g., Sweeper generates whiffs vs. RHH; strong first-pitch strike rate...",
        )
    with c2:
        st.text_area(
            "🩹 Weaknesses", key="weaknesses", height=130,
            placeholder="e.g., Fastball command glove-side; changeup still developing...",
        )
    with c3:
        st.text_area(
            "🎯 Preferences", key="preferences", height=130,
            placeholder="e.g., Like to pitch backwards when ahead; prefer ground balls with runners on...",
        )

    # --- Save / summary -----------------------------------------------------
    if st.button("💾 Save profile", type="primary"):
        if not st.session_state.throwing_hand:
            st.error("Select your throwing hand before saving.")
        elif not st.session_state.arsenal:
            st.error("Add at least one pitch to your arsenal before saving.")
        else:
            st.session_state.profile_saved = True
            st.success("Profile saved for this session!")

    if st.session_state.profile_saved and st.session_state.throwing_hand:
        name = st.session_state.pitcher_name or "Unnamed pitcher"
        n_pitches = len(st.session_state.arsenal)
        st.markdown(
            f'<div class="rec-box"><span class="rec-label">Profile summary</span><br>'
            f"{name} — {st.session_state.throwing_hand}, {n_pitches}-pitch mix. "
            f"This profile will drive AI report personalization in future versions.</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Pitch movement chart (HB vs. IVB) with synchronized numeric inputs
# ---------------------------------------------------------------------------

def _movement_key(kind: str, pitch: str) -> str:
    return f"mv_{kind}::{pitch}"


def _clear_movement_keys(pitch: str | None = None) -> None:
    """Drop stale movement-widget state (for one pitch, or all)."""
    for key in list(st.session_state.keys()):
        if not key.startswith("mv_"):
            continue
        if pitch is None or key.endswith(f"::{pitch}"):
            del st.session_state[key]


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
            p["hb"] = c_hb.number_input(
                "HB", min_value=-MOVEMENT_RANGE, max_value=MOVEMENT_RANGE,
                value=float(p.get("hb", 0.0)), step=0.5,
                key=_movement_key("hb", p["pitch"]),
                label_visibility="collapsed" if False else "visible",
            )
            p["ivb"] = c_ivb.number_input(
                "IVB", min_value=-MOVEMENT_RANGE, max_value=MOVEMENT_RANGE,
                value=float(p.get("ivb", 0.0)), step=0.5,
                key=_movement_key("ivb", p["pitch"]),
            )

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
        usage = max(p.get("usage_pct", 10), 5)
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
