"""Parser for pitcher process reports (Sockeye/cwsdata format).

Extracts: pitcher name, report date range, race-to-2K / first-pitch-strike
summaries, and per-pitch rows (type, velocity, usage, IVB, HB, spin eff).

Output schema:
{
    "pitcher_name": str | None,
    "date_range": str | None,            # "08/04/2026 - 08/09/2026"
    "race_to_2k": str | None,            # "50% (8/16)"
    "first_pitch_strikes": str | None,   # "53% (10/19)"
    "pitches": [
        {"code", "name", "velo_low", "velo_high", "velo_avg",
         "usage_count", "usage_pct", "spin_eff", "ivb", "hb", "source_page"},
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
_DATE_RANGE_RE = re.compile(
    r"^\d{2}/\d{2}/\d{4}(?:\s*-\s*\d{2}/\d{2}/\d{4})?$"
)


def parse_pitcher_report(doc: pymupdf.Document) -> dict:
    lines = [ln.strip() for ln in doc[0].get_text().splitlines() if ln.strip()]
    errors: list[str] = []

    result: dict = {
        "pitcher_name": _find_pitcher_name(lines),
        "date_range": _find_first(lines, _DATE_RANGE_RE),
        "race_to_2k": _find_after(lines, "Race to 2K", _PCT_RE),
        "first_pitch_strikes": _find_after(lines, "First-Pitch Strikes", _PCT_RE),
        "pitches": [],
        "errors": errors,
    }
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
    return result


def _parse_pitch_row(lines: list[str], start: int, usage_match: re.Match) -> tuple[dict | None, int]:
    """Parse one pitch row:
    usage, 7 pct cells, CODE, velo "lo-hi (avg)", feet-inch cells, floats.
    The trailing floats are [spin_eff,] ivb, hb — spin eff may be absent.
    """
    i = start + 1
    n = len(lines)

    # Skip the 7 percentage cells (vL/vR usage & strike splits).
    pcts = 0
    while i < n and pcts < 7 and lines[i].endswith("%"):
        pcts += 1
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

    # Release/extension cells (feet-inch), variable count.
    while i < n and _FEET_INCH_RE.match(lines[i]):
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
    return row, i - start


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


def _find_after(lines: list[str], anchor: str, pattern: re.Pattern) -> str | None:
    try:
        start = lines.index(anchor)
    except ValueError:
        return None
    for ln in lines[start + 1:start + 8]:
        if pattern.match(ln):
            return ln
    return None
