"""Combine uploaded outing reports into one season view of the arsenal.

Counts (pitches, whiffs, swings, strikes, first-pitch strikes) are summed, so
those rates are exact. Velocity/movement/release are averaged weighted by how
often the pitch was thrown in each outing. The usage-by-split columns are
shares of all pitches to LHH/RHH in an outing; the reports don't give the
number of pitches per split, so they are averaged weighted by each outing's
total pitches — an approximation, labeled as such in the UI.
"""

from __future__ import annotations

import re
from datetime import datetime

# Qualitative fields the pitcher writes; never overwritten by report data.
QUALITATIVE_FIELDS = ("notes", "plan_vs_rhh", "plan_vs_lhh", "best_counts", "confidence")
# Release numbers the pitcher typed in (inches). They override report values
# and, like the fields above, survive rebuilding the arsenal from reports.
MANUAL_RELEASE_FIELDS = ("release_height_in", "extension_in")

COUNT_OPTIONS = ["First pitch", "Ahead", "Even", "Behind", "Two strikes"]
CONFIDENCE_OPTIONS = ["Developing", "Solid", "Trusted", "Best pitch"]

_SPLITS = ("usage_vl", "usage_p2k_vl", "usage_2k_vl", "usage_vr", "usage_p2k_vr", "usage_2k_vr")
_PITCH_WEIGHTED = ("ivb", "hb", "velo_avg", "release_side_in", "release_height_in",
                   "extension_in", "in_zone_p2k")
_FRACTION_RE = re.compile(r"\((\d+)/(\d+)\)")


def outing_sort_key(outing: dict) -> datetime:
    """Latest date in '08/04/2026 - 08/09/2026' (or a single date)."""
    dates = re.findall(r"\d{2}/\d{2}/\d{4}", outing.get("date_range") or "")
    return datetime.strptime(dates[-1], "%m/%d/%Y") if dates else datetime.min


def _fraction(value: str | None) -> tuple[int, int]:
    """'68% (13/19)' -> (13, 19); missing -> (0, 0)."""
    m = _FRACTION_RE.search(value or "")
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _pct(num: float, den: float) -> float | None:
    return round(100.0 * num / den, 1) if den else None


def _weighted(pairs: list[tuple[float | None, float]]) -> float | None:
    pairs = [(v, w) for v, w in pairs if v is not None and w]
    total = sum(w for _, w in pairs)
    return round(sum(v * w for v, w in pairs) / total, 1) if total else None


def combine_outings(outings: list[dict]) -> dict:
    """Season totals per pitch plus the Race-to-2K / first-pitch-strike summary."""
    outings = sorted(outings, key=outing_sort_key)
    per_pitch: dict[str, list[tuple[dict, int]]] = {}
    for o in outings:
        total = sum(p.get("usage_count") or 0 for p in o.get("pitches", []))
        for p in o.get("pitches", []):
            per_pitch.setdefault(p["name"], []).append((p, total))

    all_pitches = sum(p.get("usage_count") or 0 for rows in per_pitch.values() for p, _ in rows)
    pitches = {}
    for name, rows in per_pitch.items():
        count = sum(p.get("usage_count") or 0 for p, _ in rows)
        swings = sum(p.get("swings") or 0 for p, _ in rows)
        firsts = sum(p.get("first_pitches") or 0 for p, _ in rows)
        stats = {
            "pitches": count,
            "outings": len(rows),
            "usage_pct": _pct(count, all_pitches),
            "velo_low": min(p["velo_low"] for p, _ in rows if p.get("velo_low") is not None),
            "velo_high": max(p["velo_high"] for p, _ in rows if p.get("velo_high") is not None),
            "whiff_pct": _pct(sum(p.get("whiffs") or 0 for p, _ in rows), swings),
            "swings": swings,
            "strike_pct": _pct(sum(p.get("strikes") or 0 for p, _ in rows), count),
            "fpk_pct": _pct(sum(p.get("fpk") or 0 for p, _ in rows), firsts),
            "first_pitches": firsts,
        }
        for key in _PITCH_WEIGHTED:
            stats[key] = _weighted([(p.get(key), p.get("usage_count") or 0) for p, _ in rows])
        for key in _SPLITS:
            stats[key] = _weighted([(p.get(key), total) for p, total in rows])
        pitches[name] = stats

    latest = outings[-1] if outings else {}
    summary = {"outings": len(outings), "pitches": all_pitches}
    for key in ("race_to_2k", "first_pitch_strikes"):
        made, total = map(sum, zip(*[_fraction(o.get(key)) for o in outings])) if outings else (0, 0)
        summary[key] = {"made": made, "total": total, "pct": _pct(made, total),
                        "season": latest.get(f"{key}_season"), "mlb": latest.get(f"{key}_mlb")}
    if outings:
        summary["first_date"] = outings[0].get("date_range")
        summary["last_date"] = latest.get("date_range")
    return {"pitches": pitches, "summary": summary}


def merge_into_arsenal(arsenal: list[dict], combined: dict) -> list[dict]:
    """Arsenal rebuilt from report numbers, keeping everything the pitcher wrote.

    Pitches from reports come first (most used first). Pitches added by hand
    that never appear in a report are kept at the end, unchanged.
    """
    existing = {p["pitch"]: p for p in arsenal}
    merged = []
    ranked = sorted(combined["pitches"].items(), key=lambda kv: -kv[1]["pitches"])
    for name, stats in ranked:
        entry = {field: existing.get(name, {}).get(field)
                 for field in QUALITATIVE_FIELDS + MANUAL_RELEASE_FIELDS}
        entry.update({
            "pitch": name,
            "velo_low": stats["velo_low"],
            "velo_high": stats["velo_high"],
            "velo_avg": stats["velo_avg"],
            "usage_pct": round(stats["usage_pct"] or 0),
            "ivb": stats["ivb"] if stats["ivb"] is not None else 0.0,
            "hb": stats["hb"] if stats["hb"] is not None else 0.0,
            "stats": stats,
            "source": "reports",
        })
        entry["notes"] = entry["notes"] or ""
        entry["best_counts"] = entry["best_counts"] or []
        merged.append(entry)
    for name, p in existing.items():
        if name in combined["pitches"]:
            continue
        if p.get("source") == "reports":
            # Its reports were deleted: keep the pitch and the notes, drop stale season stats.
            p = {k: v for k, v in p.items() if k not in ("stats", "source")}
        merged.append(p)
    return merged
