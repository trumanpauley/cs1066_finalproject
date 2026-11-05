"""Offline tests for the MLB matchup engine using synthetic Statcast rows.

Run with:  python -m pytest tests/test_mlb.py -v
"""

from __future__ import annotations

import pandas as pd
import pytest

from pitchiq.mlb.charts import zone_grid
from pitchiq.mlb.game_plan import build_game_plan
from pitchiq.mlb.hitter_profile import build_profile, describe_zone, pitch_stats, prepare

DESC_TYPE = {
    "ball": "B", "called_strike": "S", "swinging_strike": "S", "foul": "S",
    "foul_tip": "S", "hit_into_play": "X", "automatic_ball": "B",
}


def pitch(pitch_type="FF", description="ball", zone=5, p_throws="R", stand="R",
          xwoba=None, rv=0.0, strikes=0, pitch_number=2, plate_x=0.0, plate_z=2.5,
          events=None, woba_denom=None):
    return {
        "pitch_type": pitch_type, "description": description, "zone": zone,
        "type": DESC_TYPE[description], "p_throws": p_throws, "stand": stand,
        "estimated_woba_using_speedangle": xwoba, "woba_value": xwoba,
        "woba_denom": woba_denom, "events": events, "delta_run_exp": rv,
        "strikes": strikes, "pitch_number": pitch_number, "player_name": "Test, Hitter",
        "plate_x": plate_x, "plate_z": plate_z, "sz_top": 3.5, "sz_bot": 1.5,
    }


def frame(rows):
    return pd.DataFrame(rows)


# --- prepare / pitch_stats -----------------------------------------------------

def test_prepare_drops_automatic_balls_and_flags_outcomes():
    df = prepare(frame([pitch(description="automatic_ball"),
                        pitch(description="swinging_strike"),
                        pitch(description="foul_tip"),
                        pitch(description="ball", zone=13)]))
    assert len(df) == 3
    assert df["swing"].tolist() == [True, True, False]
    # Foul tips are contact, not whiffs.
    assert df["whiff"].tolist() == [True, False, False]
    assert df["out_zone"].tolist() == [False, False, True]


def test_pitch_stats_rates():
    rows = (
        [pitch(description="swinging_strike", zone=14)] * 2   # 2 chases, both whiffs
        + [pitch(description="ball", zone=14)] * 2           # 2 takes outside
        + [pitch(description="hit_into_play", zone=5, xwoba=0.900)]
        + [pitch(description="called_strike", zone=5)]
    )
    s = pitch_stats(prepare(frame(rows)))
    assert s["pitches"] == 6
    assert s["swings"] == 3
    assert s["whiff_pct"] == pytest.approx(66.7)
    assert s["chase_pct"] == 50.0
    assert s["zone_swing_pct"] == 50.0
    assert s["xwoba_con"] == 0.9


def test_profile_only_uses_pitches_from_the_requested_hand():
    rows = [pitch(p_throws="R")] * 10 + [pitch(p_throws="L", description="swinging_strike")] * 7
    assert build_profile(frame(rows), "R")["overall"]["pitches"] == 10
    assert build_profile(frame(rows), "L")["overall"]["pitches"] == 7


def test_switch_hitter_detected():
    rows = [pitch(p_throws="R", stand="L")] * 5 + [pitch(p_throws="L", stand="R")] * 5
    profile = build_profile(frame(rows), "R")
    assert profile["bats"] == "S"
    assert profile["stand"] == "L"


def test_one_mislabeled_pitch_does_not_make_a_switch_hitter():
    rows = [pitch(stand="R")] * 300 + [pitch(stand="L")]
    assert build_profile(frame(rows), "R")["bats"] == "R"


# --- zone wording (catcher's view: left = 3B side = inside to a RHH) -------------

@pytest.mark.parametrize("zone,stand,expected", [
    (1, "R", "up and in"),
    (1, "L", "up and away"),
    (9, "R", "down and away"),
    (14, "R", "down and away, off the plate"),
    (13, "L", "down and away, off the plate"),
    (5, "R", "middle-middle"),
    (2, "L", "up, middle of the plate"),
])
def test_describe_zone(zone, stand, expected):
    assert describe_zone(zone, stand) == expected


# --- game plan --------------------------------------------------------------------

def _hitter_who_crushes_fastballs_and_misses_sliders():
    rows = []
    for _ in range(30):   # fastballs: hard contact, hitter gains runs
        rows.append(pitch("FF", "hit_into_play", zone=5, xwoba=0.600, rv=0.3))
        rows.append(pitch("FF", "foul", zone=5, rv=-0.03))
    for _ in range(25):   # sliders: lots of chases and whiffs
        rows.append(pitch("SL", "swinging_strike", zone=14, rv=-0.1, strikes=2))
        rows.append(pitch("SL", "ball", zone=14, rv=0.05))
    return frame(rows)


ARSENAL = [
    {"pitch": "Fastball (4-Seam)", "usage_pct": 50},
    {"pitch": "Slider", "usage_pct": 30},
    {"pitch": "Sweeper", "usage_pct": 20},
]


def test_plan_prefers_the_pitch_he_struggles_with():
    plan = build_game_plan(build_profile(_hitter_who_crushes_fastballs_and_misses_sliders(), "R"), ARSENAL)
    assert plan["best"] == "Slider"
    assert plan["putaway"] == "Slider"
    assert plan["avoid"] == "Fastball (4-Seam)"
    assert "slider" in plan["recommendations"]["Quick"]
    assert set(plan["recommendations"]) == {"Quick", "Standard", "Detailed"}


def test_putaway_is_never_the_pitch_to_avoid():
    rows = []
    for _ in range(30):   # sweeper: misses it often, but crushes it on contact
        rows.append(pitch("ST", "swinging_strike", zone=14, rv=-0.1))
        rows.append(pitch("ST", "hit_into_play", zone=5, xwoba=0.900, rv=0.6))
    for _ in range(30):   # cutter: fewer whiffs, weak contact
        rows.append(pitch("FC", "hit_into_play", zone=5, xwoba=0.150, rv=-0.2))
        rows.append(pitch("FC", "swinging_strike", zone=14, rv=-0.1))
        rows.append(pitch("FC", "foul", zone=5, rv=-0.05))
    arsenal = [{"pitch": "Sweeper"}, {"pitch": "Cutter"}]
    plan = build_game_plan(build_profile(frame(rows), "R"), arsenal)
    assert plan["avoid"] == "Sweeper"
    assert plan["putaway"] == "Cutter"


def test_rare_pitch_falls_back_to_its_family():
    plan = build_game_plan(build_profile(_hitter_who_crushes_fastballs_and_misses_sliders(), "R"), ARSENAL)
    sweeper = next(m for m in plan["matchups"] if m["pitch"] == "Sweeper")
    # He has seen no sweepers, so his breaking-ball results (the sliders) stand in.
    assert sweeper["basis"] == "all breaking balls"
    assert sweeper["pitches"] == 50


def test_plan_with_no_data_vs_hand():
    plan = build_game_plan(build_profile(_hitter_who_crushes_fastballs_and_misses_sliders(), "L"), ARSENAL)
    assert plan["matchups"] == []
    assert "Not enough LHP data" in plan["recommendations"]["Quick"]


# --- heatmap grid -------------------------------------------------------------------

def test_zone_grid_places_pitches_in_the_right_cell():
    # Middle of the plate, middle height -> centre cell (row 2, col 2).
    rows = [pitch(description="swinging_strike", plate_x=0.0, plate_z=2.5)] * 10
    # Low and to the catcher's left, below the zone -> bottom-left cell.
    rows += [pitch(description="ball", plate_x=-1.2, plate_z=1.2)] * 12
    values, counts = zone_grid(prepare(frame(rows)), "Swing %")
    assert counts[2, 2] == 10 and values[2, 2] == 100
    assert counts[0, 0] == 12 and values[0, 0] == 0
