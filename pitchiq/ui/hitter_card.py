"""Shared hitter card + profile loading for the Scout and Team Matchup pages."""

from __future__ import annotations

import html

import streamlit as st

from pitchiq.mlb import sources
from pitchiq.mlb.charts import zone_heatmap
from pitchiq.mlb.game_plan import build_game_plan
from pitchiq.mlb.hitter_profile import build_profile

CURRENT_SEASON = 2026
MIN_PITCHES_SHOWN = 25  # pitch types he saw less often are left out of the tendencies table

THREAT_BADGES = {
    "High": '<span class="badge badge-high">High threat</span>',
    "Medium": '<span class="badge badge-medium">Medium threat</span>',
    "Low": '<span class="badge badge-low">Low threat</span>',
}

GLOSSARY = (
    "Whiff% = misses per swing · Chase% = swings at pitches outside the zone · "
    "xwOBAcon = expected wOBA on contact (higher = harder contact) · "
    "RV/100 = runs the hitter gains per 100 pitches (negative = good for you)."
)


def get_profile(hitter: dict, season: int, hand: str) -> dict:
    """Hitter profile vs. one pitcher hand, cached for the session.

    The raw Savant CSV is cached on disk by `sources`; this keeps the computed
    profile so re-rendering a card doesn't recompute it.
    """
    store = st.session_state.hitter_profiles
    key = f"{hitter['id']}:{season}:{hand}"
    if key not in store:
        raw = sources.fetch_batter_pitches(hitter["id"], season)
        if raw.empty:
            raise ValueError(f"no {season} regular-season pitches")
        profile = build_profile(raw, hand, hitter["name"], hitter["id"])
        for field in ("number", "position", "team"):
            profile[field] = hitter.get(field, "")
        store[key] = profile
    return store[key]


def render_hitter_card(profile: dict, arsenal: list[dict], mode: str, show_metrics: bool = False) -> None:
    """One hitter: header, optional stat row, game plan, tables, heatmaps."""
    card = build_game_plan(profile, arsenal)
    hand_label = f"{profile['pitcher_hand']}HP"

    with st.container(border=True):
        number = f"#{html.escape(str(profile['number']))} " if profile.get("number") else ""
        bats = card["bats"] if card["bats"] != "S" else f"S (hits {card['stand']} vs {hand_label})"
        meta = " · ".join(html.escape(x) for x in (profile.get("position", ""), profile.get("team", "")) if x)
        st.markdown(
            f'<div class="hitter-header">'
            f'<span class="hitter-name">{number}{html.escape(card["name"])}</span>'
            f'<span class="hitter-meta">{meta} · Bats: {bats}</span>'
            f'{THREAT_BADGES[card["threat"]]}</div>',
            unsafe_allow_html=True,
        )

        if show_metrics:
            _render_metrics(profile, hand_label)
        if mode != "Quick":
            st.markdown(card["summary"])

        enough_data = bool(card["matchups"]) or not arsenal
        if arsenal or not enough_data:
            st.markdown(
                f'<div class="rec-box"><span class="rec-label">How to attack</span><br>'
                f'{card["recommendations"][mode]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Add your pitches on **My Arsenal** to turn these tendencies into a game plan.")

        if mode == "Quick" or profile["overall"]["pitches"] == 0:
            return

        if card["matchups"]:
            st.markdown(f"**vs your arsenal** · his results vs {hand_label}")
            rows = [_arsenal_row(m, full=(mode == "Detailed")) for m in card["matchups"]]
            st.dataframe(rows, width="stretch", hide_index=True)

        if mode == "Detailed" or not arsenal:
            st.markdown(f"**vs every pitch type** · from {hand_label}")
            st.dataframe(_tendency_rows(profile), width="stretch", hide_index=True)

        if mode == "Detailed":
            _render_heatmaps(card, profile)
        else:
            with st.expander("Zone heatmaps"):
                _render_heatmaps(card, profile)


def _render_metrics(profile: dict, hand_label: str) -> None:
    o = profile["overall"]
    x = profile["xwoba"]
    tiles = [
        (f"PA vs {hand_label}", profile["pa"]),
        ("xwOBA", f"{x:.3f}".lstrip("0") if x is not None else "—"),
        ("K%", _pct(profile["k_pct"])),
        ("BB%", _pct(profile["bb_pct"])),
        ("Chase%", _pct(o["chase_pct"])),
        ("Whiff%", _pct(o["whiff_pct"])),
    ]
    for col, (label, value) in zip(st.columns(len(tiles)), tiles):
        col.metric(label, value)


def _pct(value) -> str:
    return "—" if value is None else f"{value:.0f}%"


def _arsenal_row(m: dict, full: bool) -> dict:
    row = {"Your pitch": m["pitch"]}
    if full:
        row.update({"Based on": m["basis"], "Pitches": m.get("pitches"), "Swing%": m.get("swing_pct")})
    row.update({"Whiff%": m.get("whiff_pct"), "Chase%": m.get("chase_pct"),
                "xwOBAcon": m.get("xwoba_con"), "RV/100": m.get("rv100")})
    return row


def _tendency_rows(profile: dict) -> list[dict]:
    total = profile["overall"]["pitches"] or 1
    seen = [(name, s) for name, s in profile["by_pitch"].items() if s["pitches"] >= MIN_PITCHES_SHOWN]
    seen.sort(key=lambda t: -t[1]["pitches"])
    return [{
        "Pitch type": name,
        "Seen%": round(100 * s["pitches"] / total, 1),
        "Swing%": s["swing_pct"],
        "Whiff%": s["whiff_pct"],
        "Chase%": s["chase_pct"],
        "xwOBAcon": s["xwoba_con"],
        "RV/100": s["rv100"],
    } for name, s in seen]


def _render_heatmaps(card: dict, profile: dict) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown("**Where he does damage**")
        st.plotly_chart(zone_heatmap(profile["pitches"], "Damage (xwOBA on contact)", card["stand"]),
                        width="stretch", key=f"dmg-{card['batter_id']}",
                        config={"displayModeBar": False})
    with right:
        st.markdown("**Where he swings and misses**")
        st.plotly_chart(zone_heatmap(profile["pitches"], "Whiff %", card["stand"]),
                        width="stretch", key=f"whf-{card['batter_id']}",
                        config={"displayModeBar": False})
