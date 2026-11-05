"""Rule-based game plan: match a pitcher's arsenal to one hitter's tendencies.

Every claim in the plan is traceable to a number in the hitter's profile, so
this layer is also the grounded input an LLM writer can build on later.

Thresholds are rough MLB reference points, not fitted values:
  xwOBA        >= .350 high threat, <= .300 low threat  (league avg ~ .315)
  1st-pitch swing >= 35% aggressive, <= 23% patient      (league avg ~ 29%)
  2-strike chase  >= 45% expands,    <= 30% disciplined   (avg ~ 39%: everyone
                  chases more with two strikes, so the bar sits above that)
Middle-middle is never reported as a hot zone: every hitter does damage there.
"""

from __future__ import annotations

from pitchiq.mlb.hitter_profile import CHASE_ZONES, IN_ZONES, PITCH_FAMILY, describe_zone

MIN_PITCHES = 40   # pitch-type sample needed before trusting it over the family
MIN_SWINGS = 15
MIN_ZONE_BIP = 6
MIN_ZONE_SWINGS = 10
MIN_ZONE_PITCHES = 20
AVOID_RV100 = 0.5  # hitter gains this many runs per 100 pitches or more

_SPOKEN = {"Fastball (4-Seam)": "4-seam fastball", "Sinker (2-Seam)": "sinker", "ChangeUp": "changeup"}


def _say(pitch: str) -> str:
    """Arsenal name as it reads in a sentence: 'Fastball (4-Seam)' -> '4-seam fastball'."""
    return _SPOKEN.get(pitch, pitch.lower())


def _fmt(value, suffix: str = "", digits: int = 0) -> str:
    if value is None:
        return "—"
    if suffix == "xwoba":
        return f"{value:.3f}".lstrip("0") if value < 1 else f"{value:.3f}"
    text = f"{value:.{digits}f}"
    if float(text) == 0:
        text = text.lstrip("-")  # no "-0.0"
    return f"{text}{suffix}"


def pitch_matchups(profile: dict, arsenal: list[dict]) -> list[dict]:
    """One row per arsenal pitch with the hitter's results against it.

    Falls back to the pitch family (fastballs / breaking / offspeed) when he
    has seen too few of that exact pitch type from this hand.
    """
    rows = []
    for pitch in arsenal:
        name = pitch["pitch"]
        stats = profile["by_pitch"].get(name)
        basis = "this pitch type"
        if not stats or stats["pitches"] < MIN_PITCHES or stats["swings"] < MIN_SWINGS:
            family = PITCH_FAMILY.get(name)
            fam_stats = profile["by_family"].get(family) if family else None
            if fam_stats and fam_stats["pitches"] >= MIN_PITCHES:
                stats, basis = fam_stats, f"all {family.lower()}"
            else:
                basis = "small sample"
        rows.append({"pitch": name, "usage_pct": pitch.get("usage_pct"), "basis": basis, **(stats or {})})
    return rows


def _zone_extremes(profile: dict) -> dict:
    """Where he does damage, where he misses, and where he chases."""
    zones, stand = profile["zones"], profile["stand"]
    damage = [(z, s["xwoba_con"]) for z in IN_ZONES
              if (s := zones[z])["bip"] >= MIN_ZONE_BIP and s["xwoba_con"] is not None]
    edges = [(z, v) for z, v in damage if z != 5]
    whiff = [(z, s["whiff_pct"]) for z in IN_ZONES + CHASE_ZONES
             if (s := zones[z])["swings"] >= MIN_ZONE_SWINGS and s["whiff_pct"] is not None]
    chase = [(z, s["swing_pct"]) for z in CHASE_ZONES
             if (s := zones[z])["pitches"] >= MIN_ZONE_PITCHES and s["swing_pct"] is not None]
    out = {}
    if damage:
        hot = max(edges or damage, key=lambda t: t[1])
        cold = min(damage, key=lambda t: t[1])
        out["hot"] = {"zone": hot[0], "where": describe_zone(hot[0], stand), "xwoba_con": hot[1]}
        out["cold"] = {"zone": cold[0], "where": describe_zone(cold[0], stand), "xwoba_con": cold[1]}
    if whiff:
        z, v = max(whiff, key=lambda t: t[1])
        out["whiff"] = {"zone": z, "where": describe_zone(z, stand), "whiff_pct": v}
    if chase:
        z, v = max(chase, key=lambda t: t[1])
        out["chase"] = {"zone": z, "where": describe_zone(z, stand), "swing_pct": v}
    return out


def threat_level(profile: dict) -> str:
    """High / Medium / Low from xwOBA vs this hand (Medium under 30 PA)."""
    x = profile["xwoba"]
    if x is None or profile["pa"] < 30:
        return "Medium"
    return "High" if x >= 0.350 else "Low" if x <= 0.300 else "Medium"


def build_game_plan(profile: dict, arsenal: list[dict]) -> dict:
    """Hitter card: threat, summary, per-pitch table, and plans per report depth."""
    hand = profile["pitcher_hand"]
    hand_label = f"{hand}HP"
    card = {
        "name": profile["name"],
        "batter_id": profile["batter_id"],
        "bats": profile["bats"],
        "stand": profile["stand"],
        "pa": profile["pa"],
        "threat": threat_level(profile),
    }

    if profile["overall"]["pitches"] < MIN_PITCHES:
        msg = (f"Not enough {hand_label} data this season "
               f"({profile['overall']['pitches']} pitches) — lean on your own scouting.")
        return {**card, "summary": msg, "matchups": [], "zones": {},
                "recommendations": {m: msg for m in ("Quick", "Standard", "Detailed")}}

    matchups = pitch_matchups(profile, arsenal)
    usable = [m for m in matchups if m.get("rv100") is not None and m["basis"] != "small sample"]
    zones = _zone_extremes(profile)
    ap = profile["approach"]

    best = min(usable, key=lambda m: m["rv100"]) if usable else None
    worst = max(usable, key=lambda m: m["rv100"]) if usable else None
    avoid = worst if worst and worst is not best and worst["rv100"] >= AVOID_RV100 else None
    # A pitch he crushes is never the put-away pitch, however often he misses it.
    whiffers = [m for m in usable if m.get("whiff_pct") is not None and m is not avoid]
    putaway = max(whiffers, key=lambda m: m["whiff_pct"]) if whiffers else best

    # --- Summary line -------------------------------------------------------
    fps = ap["first_pitch_swing_pct"]
    chase2k = ap["two_strike_chase_pct"]
    style = []
    if fps is not None:
        style.append("ambushes strike one" if fps >= 35 else "takes early" if fps <= 23 else None)
    if chase2k is not None:
        style.append("expands with two strikes" if chase2k >= 45
                     else "stays disciplined with two strikes" if chase2k <= 30 else None)
    style = [s for s in style if s]
    summary = (f"{_fmt(profile['xwoba'], 'xwoba')} xwOBA vs {hand_label} in {profile['pa']} PA · "
               f"{_fmt(profile['k_pct'], '%')} K · {_fmt(profile['bb_pct'], '%')} BB")
    if style:
        summary += f" — {' and '.join(style)}."

    # --- Building blocks ------------------------------------------------------
    if fps is not None and fps >= 35:
        strike_one = (f"He swings at {fps:.0f}% of first pitches — don't groove one. "
                      f"Start him with your {_say(best['pitch']) if best else 'best secondary pitch'} on the edge.")
    elif fps is not None and fps <= 23:
        steal = _say(best["pitch"]) if best else "fastball"
        strike_one = f"He only swings at {fps:.0f}% of first pitches — steal strike one in the zone with your {steal}."
    else:
        strike_one = f"Normal first-pitch swing rate ({_fmt(fps, '%')}) — open with your {_say(best['pitch']) if best else 'best pitch'} for a strike."

    if putaway:
        finish = f"Put-away pitch: your {_say(putaway['pitch'])} ({_fmt(putaway.get('whiff_pct'), '%')} whiff rate"
        finish += f", {chase2k:.0f}% two-strike chase)." if chase2k is not None else ")."
        if zones.get("whiff"):
            finish += f" He misses most {zones['whiff']['where']}."
    else:
        finish = "Not enough swings to pick a put-away pitch."

    caution_bits = []
    if avoid:
        caution_bits.append(f"his best results come against your {_say(avoid['pitch'])} "
                            f"({_fmt(avoid.get('xwoba_con'), 'xwoba')} xwOBA on contact)")
    if zones.get("hot"):
        caution_bits.append(f"he does damage {zones['hot']['where']} "
                            f"({_fmt(zones['hot']['xwoba_con'], 'xwoba')} xwOBA on contact)")
    caution = ("Careful: " + "; ".join(caution_bits) + ".") if caution_bits else ""

    # --- Plans by depth ---------------------------------------------------------
    quick = f"Lean on your {_say(best['pitch'])}" if best else "Attack the zone"
    if avoid:
        quick += f", stay off the {_say(avoid['pitch'])}"
    if zones.get("hot"):
        quick += f", and stay out of his hot zone ({zones['hot']['where']})"
    quick += "."

    standard = " ".join(s for s in (strike_one, finish, caution) if s)

    lines = [f"<b>0-0:</b> {strike_one}"]
    if best:
        lines.append(f"<b>Ahead:</b> Keep going to the {_say(best['pitch'])} — he produces "
                     f"{_fmt(best['rv100'], '', 1)} runs/100 against it (negative is good for you).")
    lines.append(f"<b>Two strikes:</b> {finish}")
    if avoid:
        lines.append(f"<b>Behind:</b> Don't give in with the {_say(avoid['pitch'])} "
                     f"(+{avoid['rv100']:.1f} runs/100 for him); a {_say(best['pitch'])} for a strike is safer.")
    loc = []
    if zones.get("hot"):
        loc.append(f"damage {zones['hot']['where']}")
    if zones.get("cold"):
        loc.append(f"weakest contact {zones['cold']['where']} "
                   f"({_fmt(zones['cold']['xwoba_con'], 'xwoba')})")
    if zones.get("chase"):
        loc.append(f"chases most {zones['chase']['where']} ({zones['chase']['swing_pct']:.0f}% swing)")
    if loc:
        lines.append("<b>Location:</b> " + "; ".join(loc) + ".")
    thin = [m["pitch"] for m in matchups if m["basis"] != "this pitch type"]
    if thin:
        lines.append(f"<b>Sample note:</b> few {hand_label} looks at {', '.join(thin)} — "
                     "those rows use his results vs the whole pitch family or are low-confidence.")

    return {
        **card,
        "summary": summary,
        "matchups": matchups,
        "zones": zones,
        "best": best["pitch"] if best else None,
        "avoid": avoid["pitch"] if avoid else None,
        "putaway": putaway["pitch"] if putaway else None,
        "recommendations": {"Quick": quick, "Standard": standard, "Detailed": "<br>".join(lines)},
    }
