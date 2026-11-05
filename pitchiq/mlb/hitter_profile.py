"""Turn one hitter's Statcast pitches into tendencies vs. a given pitcher hand.

All rates come straight from Savant pitch descriptions:
  swing  = any swing (whiff, foul, foul tip, ball in play)
  whiff  = swinging strike (foul tips count as contact)
  chase  = swing at a pitch in Savant zones 11-14 (outside the strike zone)
  RV/100 = run value per 100 pitches from the HITTER's side
           (positive = hitter gained runs, negative = good for the pitcher)
"""

from __future__ import annotations

import pandas as pd

# App arsenal names (config.PITCH_TYPES) -> Statcast pitch_type codes.
PITCH_CODES: dict[str, list[str]] = {
    "Fastball (4-Seam)": ["FF", "FA"],
    "Sinker (2-Seam)": ["SI"],
    "Cutter": ["FC"],
    "Slider": ["SL"],
    "Sweeper": ["ST", "SV"],
    "Curveball": ["CU", "KC", "CS"],
    "ChangeUp": ["CH"],
    "Splitter": ["FS", "FO"],
    "Knuckleball": ["KN"],
}

FAMILY_CODES: dict[str, list[str]] = {
    "Fastballs": ["FF", "FA", "SI", "FC"],
    "Breaking balls": ["SL", "ST", "SV", "CU", "KC", "CS"],
    "Offspeed": ["CH", "FS", "FO", "SC", "KN"],
}

PITCH_FAMILY: dict[str, str] = {
    "Fastball (4-Seam)": "Fastballs",
    "Sinker (2-Seam)": "Fastballs",
    "Cutter": "Fastballs",
    "Slider": "Breaking balls",
    "Sweeper": "Breaking balls",
    "Curveball": "Breaking balls",
    "ChangeUp": "Offspeed",
    "Splitter": "Offspeed",
    "Knuckleball": "Offspeed",
}

SWING_DESCRIPTIONS = {
    "swinging_strike", "swinging_strike_blocked", "foul", "foul_tip",
    "hit_into_play", "foul_bunt", "missed_bunt", "bunt_foul_tip",
}
WHIFF_DESCRIPTIONS = {"swinging_strike", "swinging_strike_blocked", "missed_bunt"}
# Not real pitches the hitter could react to.
EXCLUDED_DESCRIPTIONS = {"automatic_ball", "automatic_strike", "pitchout", "intent_ball"}

SWITCH_MIN_SHARE = 0.05

IN_ZONES = list(range(1, 10))
CHASE_ZONES = [11, 12, 13, 14]


def hand_code(throwing_hand: str | None) -> str:
    """'Right (RHP)' -> 'R', 'Left (LHP)' -> 'L'."""
    return "L" if throwing_hand and throwing_hand.lower().startswith("l") else "R"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Drop non-competitive pitches and add boolean outcome columns."""
    df = df[df["pitch_type"].notna() & ~df["description"].isin(EXCLUDED_DESCRIPTIONS)].copy()
    df["swing"] = df["description"].isin(SWING_DESCRIPTIONS)
    df["whiff"] = df["description"].isin(WHIFF_DESCRIPTIONS)
    df["in_zone"] = df["zone"].isin(IN_ZONES)
    df["out_zone"] = df["zone"].isin(CHASE_ZONES)
    df["bip"] = df["type"] == "X"
    # Expected wOBA where Statcast has it, actual wOBA otherwise (e.g. bunts).
    df["xwoba"] = df["estimated_woba_using_speedangle"].fillna(df["woba_value"])
    df["rv"] = df["delta_run_exp"].fillna(0.0)
    return df


def _pct(num: float, den: float) -> float | None:
    return round(100.0 * num / den, 1) if den else None


def pitch_stats(sub: pd.DataFrame) -> dict:
    """Swing/whiff/chase/damage summary for any slice of prepared pitches."""
    n = len(sub)
    swings = int(sub["swing"].sum())
    out_zone = int(sub["out_zone"].sum())
    in_zone = int(sub["in_zone"].sum())
    bip = sub[sub["bip"]]
    return {
        "pitches": n,
        "swings": swings,
        "bip": len(bip),
        "swing_pct": _pct(swings, n),
        "whiff_pct": _pct(int(sub["whiff"].sum()), swings),
        "chase_pct": _pct(int((sub["swing"] & sub["out_zone"]).sum()), out_zone),
        "zone_swing_pct": _pct(int((sub["swing"] & sub["in_zone"]).sum()), in_zone),
        "xwoba_con": round(float(bip["xwoba"].mean()), 3) if len(bip) else None,
        "rv100": round(float(sub["rv"].sum()) / n * 100, 2) if n else None,
    }


def build_profile(raw: pd.DataFrame, pitcher_hand: str, name: str = "", batter_id: int | None = None) -> dict:
    """Everything the game-plan engine needs about one hitter vs. one hand.

    `pitcher_hand` is 'R' or 'L'. The returned dict keeps the filtered pitch
    rows under `pitches` for heatmaps.
    """
    df = prepare(raw)
    vs = df[df["p_throws"] == pitcher_hand]

    side_counts = df["stand"].value_counts()
    stand_vs = (vs["stand"].mode().iloc[0] if len(vs)
                else side_counts.index[0] if len(side_counts) else "R")
    # Switch hitter only if the minority side is a real share: Statcast has the
    # odd mislabeled pitch (e.g. 1 of 2,207 for a right-handed hitter).
    is_switch = len(side_counts) > 1 and side_counts.iloc[-1] >= SWITCH_MIN_SHARE * side_counts.sum()
    bats = "S" if is_switch else stand_vs

    pa = vs[vs["woba_denom"] == 1]
    n_pa = len(pa)
    events = pa["events"].fillna("")
    two_strikes = vs[vs["strikes"] == 2]
    early = vs[vs["strikes"] < 2]

    return {
        "batter_id": batter_id,
        "name": name or (raw["player_name"].iloc[0] if len(raw) else "Unknown"),
        "bats": bats,              # R / L / S overall
        "stand": stand_vs,         # side he hits from vs. this pitcher hand
        "pitcher_hand": pitcher_hand,
        "pa": n_pa,
        "xwoba": round(float(pa["xwoba"].mean()), 3) if n_pa else None,
        "k_pct": _pct(int(events.isin(["strikeout", "strikeout_double_play"]).sum()), n_pa),
        "bb_pct": _pct(int(events.isin(["walk"]).sum()), n_pa),
        "overall": pitch_stats(vs),
        "approach": {
            "first_pitch_swing_pct": _pct(int(vs.loc[vs["pitch_number"] == 1, "swing"].sum()),
                                          int((vs["pitch_number"] == 1).sum())),
            "early_chase_pct": pitch_stats(early)["chase_pct"],
            "two_strike_chase_pct": pitch_stats(two_strikes)["chase_pct"],
            "two_strike_whiff_pct": pitch_stats(two_strikes)["whiff_pct"],
        },
        "by_pitch": {name_: pitch_stats(vs[vs["pitch_type"].isin(codes)])
                     for name_, codes in PITCH_CODES.items()},
        "by_family": {fam: pitch_stats(vs[vs["pitch_type"].isin(codes)])
                      for fam, codes in FAMILY_CODES.items()},
        "zones": {z: pitch_stats(vs[vs["zone"] == z]) for z in IN_ZONES + CHASE_ZONES},
        "pitches": vs,
    }


# --- Zone wording -------------------------------------------------------------
# Savant zones are numbered from the catcher's view: 1-3 top row, left to right.
# The catcher's left is the third-base side, which is INSIDE to a right-handed hitter.

_ZONE_POS = {1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (1, 0), 5: (1, 1), 6: (1, 2),
             7: (2, 0), 8: (2, 1), 9: (2, 2), 11: (0, 0), 12: (0, 2), 13: (2, 0), 14: (2, 2)}


def describe_zone(zone: int, stand: str) -> str:
    """Plain-language location of a Savant zone relative to the hitter."""
    row, col = _ZONE_POS[zone]
    vert = {0: "up", 1: "", 2: "down"}[row]
    if col == 1:
        horiz = ""
    else:
        catcher_left = col == 0
        horiz = "in" if (catcher_left == (stand == "R")) else "away"
    if zone in CHASE_ZONES:
        return f"{vert} and {horiz}, off the plate"
    if vert and horiz:
        return f"{vert} and {horiz}"
    if vert:
        return f"{vert}, middle of the plate"
    if horiz:
        return f"middle-{horiz}"
    return "middle-middle"
