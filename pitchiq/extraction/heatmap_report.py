"""Parser for opponent heatmap reports (TruMedia heatmap pages).

Each page shows one hitter's zone heatmaps against one pitcher handedness
(RHP or LHP). This parser only identifies who/what each page shows — the
heatmaps themselves are displayed as rendered images of the original page,
never re-interpreted into numbers.

Output schema:
{
    "entries": [
        {
            "number": int | None,
            "name": str,
            "bats": "R" | "L" | "S" | None,
            "team": str | None,
            "pitcher_hand": "RHP" | "LHP",
            "pitch_types": [str],
            "data_pulled": str | None,     # "4/16/2026"
            "page_number": int,            # 1-based PDF page to render
        },
    ],
    "errors": [str],
}
"""

from __future__ import annotations

import re

import pymupdf

_HEADER_RE = re.compile(r"#(\d+)\s+(.+?)\s+\((R|L|S)\)\s*(\w+)?")
_DATE_RE = re.compile(r"Data pulled on\s+(\d{1,2}/\d{1,2}/\d{4})")


def parse_heatmap_report(doc: pymupdf.Document) -> dict:
    entries: list[dict] = []
    errors: list[str] = []

    for page_index in range(len(doc)):
        page_number = page_index + 1
        lines = [
            ln.strip() for ln in doc[page_index].get_text().splitlines() if ln.strip()
        ]
        entry = _parse_page(lines, page_number)
        if entry is None:
            errors.append(f"Page {page_number}: could not identify hitter/handedness.")
        else:
            entries.append(entry)

    if not entries:
        errors.append("No heatmap pages identified — layout may have changed.")
    return {"entries": entries, "errors": errors}


def _parse_page(lines: list[str], page_number: int) -> dict | None:
    # Header lines run until a standalone RHP/LHP token.
    try:
        hand_index = next(
            i for i, ln in enumerate(lines) if ln in ("RHP", "LHP")
        )
    except StopIteration:
        return None
    pitcher_hand = lines[hand_index]

    header_text = " ".join(lines[:hand_index])
    m = _HEADER_RE.search(header_text)
    if m:
        number = int(m.group(1))
        name = re.sub(r"\s+", " ", m.group(2)).strip()
        bats = m.group(3)
        team = m.group(4)
    elif header_text.strip():
        number, name, bats, team = None, header_text.strip(), None, None
    else:
        return None

    # Pitch types: lines after the hand token until metadata lines.
    pitch_types: list[str] = []
    for ln in lines[hand_index + 1:]:
        if ln.startswith(("Seasons:", "Data pulled", "Game Type")) or re.match(
            r"^\d+ of \d+$", ln
        ):
            break
        pitch_types.append(ln)

    date_match = _DATE_RE.search(" ".join(lines))

    return {
        "number": number,
        "name": name,
        "bats": bats,
        "team": team,
        "pitcher_hand": pitcher_hand,
        "pitch_types": pitch_types,
        "data_pulled": date_match.group(1) if date_match else None,
        "page_number": page_number,
    }
