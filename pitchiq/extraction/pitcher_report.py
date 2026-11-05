"""Parser for pitcher process reports (Sockeye/cwsdata format).

Extracts: pitcher name, report date range, race-to-2K / first-pitch-strike
summaries (outing, season, MLB), per-pitch rows from page 1 (usage incl.
splits by hitter side and count, velocity, release, extension, IVB, HB, spin
eff), and per-pitch results from page 2 (whiffs, strikes, first-pitch strikes).
The location plots on page 2 are images and are not extracted.

Output schema:
{
    "pitcher_name": str | None,
    "date_range": str | None,            # "08/04/2026 - 08/09/2026"
    "race_to_2k": str | None,            # "50% (8/16)"  (this outing)
    "race_to_2k_season": str | None,     # "60%"
    "race_to_2k_mlb": str | None,        # "64%"
    "first_pitch_strikes": str | None,   # "53% (10/19)"
    "first_pitch_strikes_season": str | None,
    "first_pitch_strikes_mlb": str | None,
    "pitches": [
        {"code", "name", "velo_low", "velo_high", "velo_avg",
         "usage_count", "usage_pct", "spin_eff", "ivb", "hb", "source_page",
         # usage share of all pitches in that split (columns sum to ~100%):
         "usage_vl", "usage_p2k_vl", "usage_2k_vl",
         "usage_vr", "usage_p2k_vr", "usage_2k_vr",
         "in_zone_p2k",                    # this pitch's in-zone % before 2 strikes
         "release_side_in", "release_height_in", "extension_in",
         "whiffs", "swings", "strikes", "fpk", "first_pitches"},  # page 2
    ],
    "errors": [str],
}

Missing cells (e.g. an empty Spin Eff column) are preserved as None.
"""

from __future__ import annotations

import re

import pymupdf

# Sockeye pitch-type codes -> readable names.
PITCH_CODE_NAMES = {
    "FF": "Fastball (4-Seam)",
    "FT": "Sinker (2-Seam)",
    "SI": "Sinker (2-Seam)",
    "FC": "Cutter",
    "SL": "Slider",
    "SW": "Sweeper",
    "CB": "Curveball",
    "CU": "Curveball",
    "CH": "ChangeUp",
    "FS": "Splitter",
    "KN": "Knuckleball",
}

_USAGE_RE = re.compile(r"^(\d+)\s*\((\d+)%\)$")
_VELO_RE = re.compile(r"^(\d+)-(\d+)\s*\((\d+)\)$")
_FEET_INCH_RE = re.compile(r"^\d+'\d+\"$")
_FLOAT_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_PCT_RE = re.compile(r"^\d+%\s*\(\d+/\d+\)$")
_FRACTION_RE = re.compile(r"^(Whiffs|Strikes|FPK):\s*(\d+)/(\d+)$")
_SPLIT_COLUMNS = ["usage_vl", "usage_p2k_vl", "usage_2k_vl",
                  "usage_vr", "usage_p2k_vr", "usage_2k_vr", "in_zone_p2k"]
_DATE_RANGE_RE = re.compile(
    r"^\d{2}/\d{2}/\d{4}(?:\s*-\s*\d{2}/\d{2}/\d{4})?$"
)


def parse_pitcher_report(doc: pymupdf.Document) -> dict:
    lines = [ln.strip() for ln in doc[0].get_text().splitlines() if ln.strip()]
    errors: list[str] = []

    result: dict = {
        "pitcher_name": _find_pitcher_name(lines),
        "date_range": _find_first(lines, _DATE_RANGE_RE),
        "pitches": [],
        "errors": errors,
    }
    for key, anchor in (("race_to_2k", "Race to 2K"), ("first_pitch_strikes", "First-Pitch Strikes")):
        outing, season, mlb = _find_summary(lines, anchor)
        result[key], result[f"{key}_season"], result[f"{key}_mlb"] = outing, season, mlb

    if not result["pitcher_name"]:
        errors.append("Pitcher name not found on page 1.")
    if not result["date_range"]:
        errors.append("Report date range not found.")

    # Walk lines; a usage cell like "33 (43%)" starts a pitch row.
    i = 0
    while i < len(lines):
        m = _USAGE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        row, consumed = _parse_pitch_row(lines, i, m)
        if row:
            row["source_page"] = 1
            result["pitches"].append(row)
            i += consumed
        else:
            errors.append(f"Could not parse pitch row starting at '{lines[i]}'.")
            i += 1

    if not result["pitches"]:
        errors.append("No pitch rows found — layout may have changed.")
    elif len(doc) > 1:
        _merge_page2_results(doc[1], result)
    return result


def _merge_page2_results(page: pymupdf.Page, result: dict) -> None:
    """Attach 'Whiffs: 8/13', 'Strikes: 21/32', 'FPK: 7/7' under each pitch code."""
    lines = [ln.strip() for ln in page.get_text().splitlines() if ln.strip()]
    by_code = {p["code"]: p for p in result["pitches"]}
    fields = {"Whiffs": ("whiffs", "swings"), "Strikes": ("strikes", None), "FPK": ("fpk", "first_pitches")}
    current = None
    for ln in lines:
        if ln in by_code:
            current = by_code[ln]
            continue
        m = _FRACTION_RE.match(ln)
        if m and current is not None:
            made_key, total_key = fields[m.group(1)]
            current[made_key] = int(m.group(2))
            if total_key:
                current[total_key] = int(m.group(3))
    missing = [code for code, p in by_code.items() if "strikes" not in p]
    if missing:
        result["errors"].append(f"Page 2 results not found for: {', '.join(missing)}.")


def _parse_pitch_row(lines: list[str], start: int, usage_match: re.Match) -> tuple[dict | None, int]:
    """Parse one pitch row:
    usage, 7 pct cells, CODE, velo "lo-hi (avg)", feet-inch cells, floats.
    The trailing floats are [spin_eff,] ivb, hb — spin eff may be absent.
    """
    i = start + 1
    n = len(lines)

    # 7 percentage cells: usage vs LHH (all / pre-2K / 2K), vs RHH, pre-2K in-zone.
    pcts: list[int] = []
    while i < n and len(pcts) < 7 and re.fullmatch(r"\d+%", lines[i]):
        pcts.append(int(lines[i][:-1]))
        i += 1

    # Pitch code
    if i >= n or not re.fullmatch(r"[A-Z]{2,3}", lines[i]):
        return None, 1
    code = lines[i]
    i += 1

    # Velocity
    if i >= n:
        return None, 1
    vm = _VELO_RE.match(lines[i])
    if not vm:
        return None, 1
    i += 1

    # Release side, release height, extension (feet-inch cells).
    feet_inch: list[float] = []
    while i < n and _FEET_INCH_RE.match(lines[i]):
        feet_inch.append(_to_inches(lines[i]))
        i += 1

    # Optional spin efficiency, reported as a percentage (e.g. "87%").
    spin_eff = None
    if i < n and re.fullmatch(r"\d+%", lines[i]):
        spin_eff = float(lines[i][:-1])
        i += 1

    # Trailing numeric cells until the next usage cell / non-float.
    floats: list[float] = []
    while i < n and len(floats) < 3 and _FLOAT_RE.match(lines[i]) and not _USAGE_RE.match(lines[i]):
        floats.append(float(lines[i]))
        i += 1

    if len(floats) == 3 and spin_eff is None:
        spin_eff, ivb, hb = floats
    elif len(floats) >= 2:
        ivb, hb = floats[0], floats[1]
    else:
        return None, 1

    row = {
        "code": code,
        "name": PITCH_CODE_NAMES.get(code, code),
        "velo_low": int(vm.group(1)),
        "velo_high": int(vm.group(2)),
        "velo_avg": int(vm.group(3)),
        "usage_count": int(usage_match.group(1)),
        "usage_pct": int(usage_match.group(2)),
        "spin_eff": spin_eff,
        "ivb": ivb,
        "hb": hb,
    }
    # P2K IZ (last column) is blank when the pitch wasn't thrown before 2 strikes,
    # leaving 6 cells; the other six are always present.
    if len(pcts) in (6, 7):
        row.update(dict(zip(_SPLIT_COLUMNS, pcts)))
        row.setdefault("in_zone_p2k", None)
    if len(feet_inch) == 3:
        row["release_side_in"], row["release_height_in"], row["extension_in"] = feet_inch
    return row, i - start


def _to_inches(cell: str) -> float:
    """\"5'8\"\" -> 68.0"""
    feet, inches = cell.rstrip('"').split("'")
    return int(feet) * 12 + float(inches)


def _find_summary(lines: list[str], anchor: str) -> tuple[str | None, str | None, str | None]:
    """Race to 2K / First-Pitch Strikes block: Range, 2026, MLB headers then
    the outing value '68% (13/19)', the season '61%', and MLB '64%'."""
    try:
        start = lines.index(anchor)
    except ValueError:
        return None, None, None
    window = lines[start + 1:start + 10]
    for j, ln in enumerate(window):
        if _PCT_RE.match(ln):
            rest = [x for x in window[j + 1:j + 3] if re.fullmatch(r"\d+%", x)]
            return ln, *(rest + [None, None])[:2]
    return None, None, None


def _find_pitcher_name(lines: list[str]) -> str | None:
    for ln in lines:
        m = re.match(r"^(.*)\s+Pitching Report$", ln)
        if m:
            return m.group(1).strip()
    return None


def _find_first(lines: list[str], pattern: re.Pattern) -> str | None:
    for ln in lines:
        if pattern.match(ln):
            return ln
    return None
