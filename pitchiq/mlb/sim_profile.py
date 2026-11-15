"""Convert Baseball Savant hitter profiles and the user's arsenal into
Pitch Simulator data (the JSON shapes in simulator/src/engine/types.ts).

Every hitter rate is measured from the hitter's own Statcast pitches vs. the
selected pitcher hand. Small samples are shrunk toward a prior so a hitter
who saw 12 changeups doesn't get an extreme multiplier:

    rate = (successes + prior * K) / (trials + K)

The priors below are rounded MLB-wide ballpark figures used only for that
shrinkage — with a normal sample the hitter's own numbers dominate.
"""

from __future__ import annotations

import math

import pandas as pd

from pitchiq.mlb.hitter_profile import FAMILY_CODES, PITCH_FAMILY

# --- Shrinkage priors (approximate league-wide rates) -------------------------
PRIOR = {
    "zone_swing": 0.67,
    "chase": 0.28,
    "zone_contact": 0.82,
    "out_contact": 0.56,
    "foul_share": 0.50,
    "exit_velo": 88.5,
    "launch_angle": 12.0,
}
K_RATE = 40      # pseudo-pitches for rate shrinkage
K_BIP = 25       # pseudo-balls-in-play for batted-ball means

FOUL_DESCRIPTIONS = {"foul", "foul_tip", "foul_bunt", "bunt_foul_tip"}

# Simulator pitch families (engine PitchCategory) <- hitter_profile families.
_SIM_FAMILY = {"Fastballs": "fastball", "Breaking balls": "breaking", "Offspeed": "offspeed"}

# Arsenal names (config.PITCH_TYPES) -> Statcast codes the simulator shows.
PITCH_CODE = {
    "Fastball (4-Seam)": "FF", "Sinker (2-Seam)": "SI", "Cutter": "FC",
    "Slider": "SL", "Sweeper": "ST", "Curveball": "CU",
    "ChangeUp": "CH", "Splitter": "FS", "Knuckleball": "KN",
}
DISPLAY_NAME = {
    "Fastball (4-Seam)": "Four-Seam Fastball", "Sinker (2-Seam)": "Sinker",
    "ChangeUp": "Changeup",
}
# Fallbacks only when the arsenal entry leaves a field blank: typical
# velocity (mph), arm-side HB and IVB (inches) for each pitch type.
TYPICAL = {
    "Fastball (4-Seam)": (94, 7, 16), "Sinker (2-Seam)": (93, 15, 8),
    "Cutter": (89, -2, 9), "Slider": (85, -5, 1), "Sweeper": (82, -14, 0),
    "Curveball": (79, -8, -10), "ChangeUp": (85, 14, 7), "Splitter": (86, 10, 3),
    "Knuckleball": (75, 0, 0),
}
# Location scatter (1 SD, feet) when no command data exists: fastballs are
# typically located more precisely than breaking and offspeed pitches.
COMMAND_SD = {"fastball": 0.30, "breaking": 0.38, "offspeed": 0.36}


def _col(df: pd.DataFrame, name: str, default=float("nan")) -> pd.Series:
    """A Statcast column, or a constant series if the export lacks it."""
    return df[name] if name in df.columns else pd.Series(default, index=df.index, dtype=float)


def _shrink(num: float, den: float, prior: float, k: float = K_RATE) -> float:
    return (num + prior * k) / (den + k)


def _ratio(value: float, base: float, lo: float = 0.5, hi: float = 1.6) -> float:
    if not base:
        return 1.0
    return round(min(hi, max(lo, value / base)), 3)


def _discipline(df: pd.DataFrame, prior: dict[str, float]) -> dict[str, float]:
    """Zone swing, chase, zone/out contact, and foul share for a pitch slice."""
    zone = df[df["in_zone"]]
    out = df[df["out_zone"]]
    zs, os_ = zone[zone["swing"]], out[out["swing"]]
    contact = df[df["swing"] & ~df["whiff"]]
    fouls = int(contact["description"].isin(FOUL_DESCRIPTIONS).sum())
    return {
        "zoneSwing": _shrink(len(zs), len(zone), prior["zone_swing"]),
        "chase": _shrink(len(os_), len(out), prior["chase"]),
        "zoneContact": _shrink(int((~zs["whiff"]).sum()), len(zs), prior["zone_contact"]),
        "outZoneContact": _shrink(int((~os_["whiff"]).sum()), len(os_), prior["out_contact"]),
        "foulShare": _shrink(fouls, len(contact), prior["foul_share"]),
    }


def _xwoba_con(df: pd.DataFrame) -> tuple[float, int]:
    bip = df[df["bip"]]["xwoba"].dropna()
    return (float(bip.mean()) if len(bip) else 0.0), len(bip)


def _spray_degrees(df: pd.DataFrame) -> pd.Series:
    """Statcast hit coordinates -> spray angle (0 = center, negative = left field)."""
    hc = pd.DataFrame({"hc_x": _col(df, "hc_x"), "hc_y": _col(df, "hc_y")}).dropna()
    if hc.empty:
        return pd.Series(dtype=float)
    return hc.apply(lambda r: math.degrees(math.atan2(r["hc_x"] - 125.42, 198.27 - r["hc_y"])), axis=1)


def simulator_hitter(profile: dict, season: int) -> dict:
    """One hitter in the simulator's HitterProfile shape."""
    vs: pd.DataFrame = profile["pitches"]
    hand = profile["pitcher_hand"]
    stand = profile["stand"] if profile["stand"] in ("R", "L") else "R"

    base = _discipline(vs, PRIOR)
    base_prior = {"zone_swing": base["zoneSwing"], "chase": base["chase"],
                  "zone_contact": base["zoneContact"], "out_contact": base["outZoneContact"],
                  "foul_share": base["foulShare"]}
    base_contact = _shrink(int((vs["swing"] & ~vs["whiff"]).sum()), int(vs["swing"].sum()),
                           (base["zoneContact"] + base["outZoneContact"]) / 2)
    base_x, _ = _xwoba_con(vs)

    by_type = {}
    for fam, codes in FAMILY_CODES.items():
        sub = vs[vs["pitch_type"].isin(codes)]
        d = _discipline(sub, base_prior)
        contact = _shrink(int((sub["swing"] & ~sub["whiff"]).sum()), int(sub["swing"].sum()), base_contact)
        fam_x, fam_n = _xwoba_con(sub)
        damage = _shrink(fam_x * fam_n, fam_n, base_x, K_BIP) if base_x else 0
        by_type[_SIM_FAMILY[fam]] = {
            "zoneSwingMult": _ratio(d["zoneSwing"], base["zoneSwing"]),
            "chaseMult": _ratio(d["chase"], base["chase"]),
            "contactMult": _ratio(contact, base_contact, 0.6, 1.3),
            "damageMult": _ratio(damage, base_x, 0.8, 1.2) if base_x else 1.0,
        }

    swing_all = _shrink(int(vs["swing"].sum()), len(vs), 0.47)

    def count_mult(mask: pd.Series) -> float:
        sub = vs[mask]
        return _ratio(_shrink(int(sub["swing"].sum()), len(sub), swing_all), swing_all, 0.1, 2.0)

    balls, strikes = _col(vs, "balls", 0), _col(vs, "strikes", 0)
    counts = {
        "firstPitchSwingMult": count_mult((balls == 0) & (strikes == 0)),
        "hitterAheadSwingMult": count_mult((balls > strikes) & ~((balls == 3) & (strikes == 0))),
        "threeBallsNoStrikesSwingMult": count_mult((balls == 3) & (strikes == 0)),
        "twoStrikeSwingMult": count_mult(strikes == 2),
    }

    bip = vs[vs["bip"]]
    ev = _col(bip, "launch_speed").dropna()
    la = _col(bip, "launch_angle").dropna()
    spray = _spray_degrees(bip)
    pull = -spray if stand == "R" else spray
    batted = {
        "exitVeloMean": round(_shrink(float(ev.sum()), len(ev), PRIOR["exit_velo"], K_BIP), 1),
        "exitVeloSd": round(float(ev.std()) if len(ev) > 10 else 14.0, 1),
        "launchAngleMean": round(_shrink(float(la.sum()), len(la), PRIOR["launch_angle"], K_BIP), 1),
        "launchAngleSd": round(min(35.0, max(15.0, float(la.std()))) if len(la) > 10 else 26.0, 1),
        "pullBias": round(float(pull.mean()) if len(pull) > 10 else 5.0, 1),
        "spraySd": round(min(35.0, max(12.0, float(spray.std()))) if len(spray) > 10 else 24.0, 1),
    }

    zone = {"bottom": 1.6, "top": 3.4}
    bot, top = _col(vs, "sz_bot").dropna(), _col(vs, "sz_top").dropna()
    if len(bot) and len(top):
        zone = {"bottom": round(float(bot.mean()), 2), "top": round(float(top.mean()), 2)}

    overall = profile["overall"]
    blurb_bits = []
    if profile.get("xwoba") is not None:
        blurb_bits.append(f"{profile['xwoba']:.3f} xwOBA in {profile['pa']} PA".replace("0.", ".", 1))
    if overall.get("chase_pct") is not None:
        blurb_bits.append(f"{overall['chase_pct']:.0f}% chase")
    if overall.get("whiff_pct") is not None:
        blurb_bits.append(f"{overall['whiff_pct']:.0f}% whiff")

    return {
        "id": str(profile.get("batter_id") or profile["name"]),
        "name": profile["name"],
        "bats": stand,
        "number": str(profile.get("number") or ""),
        "position": profile.get("position") or "",
        "team": profile.get("team") or "",
        "blurb": f"vs {hand}HP: " + " · ".join(blurb_bits) if blurb_bits else "",
        "zone": zone,
        "rates": {k: round(v, 3) for k, v in base.items()},
        "byPitchType": by_type,
        "counts": counts,
        "battedBall": batted,
        "source": {
            "kind": "api",
            "label": f"Baseball Savant {season} regular season vs {hand}HP · {len(vs):,} pitches",
        },
    }


def simulator_pitcher(arsenal: list[dict], throwing_hand: str | None, name: str = "") -> dict | None:
    """The user's My Arsenal as a simulator PitcherProfile (None if empty)."""
    pitches = []
    known = [p for p in arsenal if p.get("pitch") in PITCH_CODE]
    total_usage = sum(float(p.get("usage_pct") or 0) for p in known)
    for p in arsenal:
        pitch = p.get("pitch")
        if pitch not in PITCH_CODE:
            continue
        family = _SIM_FAMILY[PITCH_FAMILY[pitch]]
        velo_t, hb_t, ivb_t = TYPICAL[pitch]
        lo, hi = p.get("velo_low"), p.get("velo_high")
        velo = p.get("velo_avg") or ((lo + hi) / 2 if lo and hi else lo or hi or velo_t)
        usage = float(p.get("usage_pct") or 0)
        pitches.append({
            "code": PITCH_CODE[pitch],
            "name": DISPLAY_NAME.get(pitch, pitch),
            "category": family,
            "velocity": round(float(velo), 1),
            "velocitySd": round(max(0.6, (hi - lo) / 4), 2) if lo and hi and hi > lo else 0.8,
            "horizontalBreak": float(p["hb"]) if p.get("hb") is not None else float(hb_t),
            "inducedVerticalBreak": float(p["ivb"]) if p.get("ivb") is not None else float(ivb_t),
            "usage": round(usage / total_usage, 3) if total_usage else round(1 / len(known), 3),
            "command": {"sdX": COMMAND_SD[family], "sdZ": COMMAND_SD[family]},
        })
    if not pitches:
        return None

    hand = "L" if throwing_hand and throwing_hand.lower().startswith("l") else "R"
    ext = next((p.get("extension_in") for p in arsenal if p.get("extension_in")), None)
    height = next((p.get("release_height_in") for p in arsenal if p.get("release_height_in")), None)
    return {
        "id": "my-arsenal",
        "name": name or "My Arsenal",
        "hand": hand,
        # Release x is from the catcher's view: a righty releases on the third-base side.
        "release": {
            "x": -1.8 if hand == "R" else 1.8,
            "z": round(height / 12, 2) if height else 5.9,
            "extension": round(ext / 12, 2) if ext else 6.3,
        },
        "pitches": pitches,
        "source": {"kind": "synthetic", "label": "Your My Arsenal profile"},
    }
