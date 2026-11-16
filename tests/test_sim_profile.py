"""Savant hitter profile + My Arsenal -> Pitch Simulator data (offline).

Run with:  python -m pytest tests/test_sim_profile.py -v
"""

from __future__ import annotations

import json

import pandas as pd

from pitchiq.mlb.hitter_profile import build_profile
from pitchiq.mlb.sim_profile import simulator_hitter, simulator_pitcher
from pitchiq.ui.simulator import _with_data

DESC_TYPE = {"ball": "B", "called_strike": "S", "swinging_strike": "S", "foul": "S",
             "hit_into_play": "X"}


def pitch(pitch_type="FF", description="ball", zone=5, p_throws="R", stand="R",
          balls=0, strikes=0, pitch_number=2, ev=None, la=None, hc=(None, None)):
    xw = 0.4 if description == "hit_into_play" else None
    return {
        "pitch_type": pitch_type, "description": description, "zone": zone,
        "type": DESC_TYPE[description], "p_throws": p_throws, "stand": stand,
        "estimated_woba_using_speedangle": xw, "woba_value": xw, "woba_denom": None,
        "events": None, "delta_run_exp": 0.0, "balls": balls, "strikes": strikes,
        "pitch_number": pitch_number, "player_name": "Test, Hitter",
        "plate_x": 0.0, "plate_z": 2.5, "sz_top": 3.4, "sz_bot": 1.55,
        "launch_speed": ev, "launch_angle": la, "hc_x": hc[0], "hc_y": hc[1],
    }


def chaser_rows() -> list[dict]:
    """A free swinger who chases breaking balls and pulls the ball."""
    rows = []
    for _ in range(60):  # breaking balls off the plate: mostly chased and missed
        rows.append(pitch("SL", "swinging_strike", zone=14))
    for _ in range(20):
        rows.append(pitch("SL", "ball", zone=14))
    for _ in range(60):  # fastballs off the plate: mostly taken
        rows.append(pitch("FF", "ball", zone=11))
    for _ in range(10):
        rows.append(pitch("FF", "foul", zone=11))
    for _ in range(80):  # fastballs in the zone: swung at, put in play, pulled
        rows.append(pitch("FF", "hit_into_play", zone=5, ev=100, la=18, hc=(80, 120)))
    for _ in range(20):
        rows.append(pitch("FF", "called_strike", zone=5))
    for _ in range(30):  # some left-handed pitching that must be ignored vs RHP
        rows.append(pitch("CH", "swinging_strike", zone=5, p_throws="L"))
    return rows


def sim(rows, hand="R"):
    profile = build_profile(pd.DataFrame(rows), hand, "Test Hitter", 123)
    profile.update(number="7", position="SS", team="MIL")
    return simulator_hitter(profile, 2026)


def test_rates_are_probabilities_and_follow_the_data():
    h = sim(chaser_rows())
    for v in h["rates"].values():
        assert 0 <= v <= 1
    # 70 of 150 out-of-zone pitches chased, shrunk toward a .28 prior.
    assert 0.40 < h["rates"]["chase"] < 0.47
    # Every in-zone swing made contact.
    assert h["rates"]["zoneContact"] > 0.9


def test_pitch_type_tendencies_reflect_the_split():
    t = sim(chaser_rows())["byPitchType"]
    assert t["breaking"]["chaseMult"] > 1.3       # chases sliders far more
    assert t["fastball"]["chaseMult"] < 0.6       # rarely chases fastballs
    assert t["breaking"]["contactMult"] < t["fastball"]["contactMult"]


def test_only_pitches_from_the_selected_hand_count():
    # The lefty changeups (all whiffs in the zone) would tank zone contact.
    assert sim(chaser_rows(), "R")["rates"]["zoneContact"] > 0.9


def test_batted_ball_and_identity_fields():
    h = sim(chaser_rows())
    bb = h["battedBall"]
    assert 95 < bb["exitVeloMean"] < 100           # 80 balls at 100 mph, shrunk toward 88.5
    assert bb["pullBias"] > 20                     # hc_x < 125 is left field: pulled by a righty
    assert h["bats"] == "R" and h["team"] == "MIL" and h["number"] == "7"
    assert h["zone"] == {"bottom": 1.55, "top": 3.4}
    assert h["source"]["kind"] == "api" and "Baseball Savant 2026" in h["source"]["label"]


def test_thin_samples_fall_back_toward_priors():
    h = sim([pitch("FF", "ball", zone=11), pitch("FF", "hit_into_play", zone=5)])
    assert abs(h["rates"]["chase"] - 0.28) < 0.03
    assert h["battedBall"]["exitVeloSd"] == 14.0


def test_simulator_pitcher_from_arsenal():
    arsenal = [
        {"pitch": "Fastball (4-Seam)", "velo_low": 90, "velo_high": 94, "usage_pct": 60, "ivb": 18, "hb": 6},
        {"pitch": "Sweeper", "velo_low": 80, "velo_high": 84, "usage_pct": 40, "ivb": None, "hb": None},
        {"pitch": "Eephus", "usage_pct": 5},  # unknown pitch types are skipped
    ]
    p = simulator_pitcher(arsenal, "Left (LHP)", "Me")
    assert p["hand"] == "L" and p["release"]["x"] > 0
    assert [x["code"] for x in p["pitches"]] == ["FF", "ST"]
    ff, st = p["pitches"]
    assert ff["velocity"] == 92 and ff["horizontalBreak"] == 6
    assert st["category"] == "breaking" and st["horizontalBreak"] < 0   # typical sweep fills the blank
    assert abs(sum(x["usage"] for x in p["pitches"]) - 1) < 0.01
    assert simulator_pitcher([], "Right (RHP)") is None


def test_data_injection_is_valid_and_script_safe():
    page = "<!doctype html><html><head><title>x</title></head><body></body></html>"
    out = _with_data(page, {"team": "Evil </script><script>alert(1)</script>", "hitters": []})
    assert out.count("</script>") == 1          # only the injected tag's own closer
    payload = out.split("window.PITCHIQ_DATA = ", 1)[1].split(";</script>", 1)[0]
    assert json.loads(payload)["team"].startswith("Evil")


def test_per_pitch_release_prefers_typed_values_then_reports():
    arsenal = [
        # typed on My Arsenal (inches): 6'2" high, 7'0" extension
        {"pitch": "Fastball (4-Seam)", "velo_low": 92, "velo_high": 96, "usage_pct": 50,
         "ivb": 17, "hb": 8, "release_height_in": 74, "extension_in": 84,
         "stats": {"release_height_in": 70, "extension_in": 75}},
        # only report numbers
        {"pitch": "Slider", "velo_low": 84, "velo_high": 87, "usage_pct": 30, "ivb": 1, "hb": -6,
         "stats": {"release_height_in": 69, "extension_in": 72}},
        # nothing: falls back to the pitcher-level average
        {"pitch": "ChangeUp", "velo_low": 84, "velo_high": 87, "usage_pct": 20, "ivb": 7, "hb": 14},
    ]
    p = simulator_pitcher(arsenal, "Right (RHP)")
    ff, sl, ch = p["pitches"]
    assert ff["release"] == {"z": round(74 / 12, 2), "extension": 7.0}
    assert sl["release"] == {"z": round(69 / 12, 2), "extension": 6.0}
    assert "release" not in ch
    assert p["release"]["extension"] == 6.5          # mean of 7.0 and 6.0
    assert p["release"]["z"] == 5.96                 # mean of 6.17 and 5.75


def test_rebuilding_from_reports_keeps_typed_release():
    from pitchiq.arsenal import merge_into_arsenal

    arsenal = [{"pitch": "Slider", "notes": "", "release_height_in": 70.0, "extension_in": 80.0}]
    combined = {"pitches": {"Slider": {"pitches": 40, "velo_low": 84, "velo_high": 87, "velo_avg": 85,
                                        "usage_pct": 100, "ivb": 1, "hb": -6, "extension_in": 72}}}
    merged = merge_into_arsenal(arsenal, combined)
    assert merged[0]["extension_in"] == 80.0 and merged[0]["release_height_in"] == 70.0


def test_scout_report_matches_scout_page_content():
    from pitchiq.mlb.game_plan import build_game_plan
    from pitchiq.ui.simulator import scout_report

    profile = build_profile(pd.DataFrame(chaser_rows()), "R", "Test Hitter", 123)
    profile.update(number="7", position="SS", team="MIL")
    arsenal = [{"pitch": "Fastball (4-Seam)", "usage_pct": 60}, {"pitch": "Slider", "usage_pct": 40}]
    r = scout_report(profile, arsenal)
    card = build_game_plan(profile, arsenal)

    assert r["threat"] == card["threat"] and r["number"] == "7" and r["meta"] == "SS · MIL"
    assert r["quick"] == card["recommendations"]["Quick"]
    assert "<" not in r["standard"] and "<" not in r["summary"]
    # Detailed plan arrives as labeled lines ("0-0", "Two strikes", ...), no HTML.
    labels = [line["label"] for line in r["detailed"]]
    assert "0-0" in labels and "Two strikes" in labels
    assert all("<" not in line["text"] for line in r["detailed"])
    assert [row["Your pitch"] for row in r["arsenalRows"]] == ["Fastball (4-Seam)", "Slider"]
    assert len(r["metrics"]) == 6 and r["hasArsenal"]
    json.dumps(r)  # the payload must be JSON-serializable for the simulator
