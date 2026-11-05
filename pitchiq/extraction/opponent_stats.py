"""Parser for opponent statistical reports (TruMedia grid format).

Uses word coordinates (not reading order) so missing cells ("-") stay in the
correct column. Each hitter block has side-by-side "vs. RHP" and "vs. LHP"
tables with rows per pitch type.

Output schema:
{
    "hitters": [
        {
            "number": int | None,
            "name": str,
            "bats": "R" | "L" | "S" | None,
            "team": str | None,
            "source_page": int,              # 1-based PDF page
            "splits": {
                "vs. RHP": [ {"Pitch", "P", <stat>: float | None, ...}, ... ],
                "vs. LHP": [ ... ],
            },
        },
    ],
    "errors": [str],
}

Stat values: percentages become floats (23.3), AVG/ISO/wOBA become floats
(0.306), and "-" (no data) becomes None. The P column preserves sample size.
"""

from __future__ import annotations

import re

import pymupdf

STAT_COLUMNS = [
    "FPSwing%", "InZoneWhiff%", "Pre2K-Ch%", "2K-Ch%",
    "SoftCt%", "Ground%", "AVG", "ISO", "wOBA",
]

PITCH_LABELS = {
    "Total", "Fastball", "Sinker", "Cutter", "Curveball",
    "Slider", "Sweeper", "ChangeUp", "Splitter", "Knuckleball",
}

_HEADER_RE = re.compile(
    r"#(\d+)\s+(.+?)\s+\((R|L|S)\)\s*(\w+)?", re.DOTALL
)

_ROW_TOL = 3.0      # y tolerance when grouping words into rows
_NAME_MAX_X = 120.0  # words left of this are part of the hitter header
_SIDE_SPLIT_X = 440.0  # boundary between the vs. RHP and vs. LHP tables


def parse_opponent_stats(doc: pymupdf.Document) -> dict:
    hitters: list[dict] = []
    errors: list[str] = []

    for page_index in range(len(doc)):
        words = doc[page_index].get_text("words")
        anchors = _find_block_anchors(words)
        if not anchors and page_index == 0:
            errors.append("No 'vs. RHP' table anchors found on page 1.")
        for bi, (y_top, y_bottom) in enumerate(anchors):
            block_words = [w for w in words if y_top <= w[1] < y_bottom]
            hitter = _parse_hitter_block(block_words, page_index + 1)
            if hitter is None:
                errors.append(
                    f"Page {page_index + 1}: could not parse hitter block {bi + 1}."
                )
            else:
                hitters.append(hitter)

    if not hitters:
        errors.append("No hitters extracted — layout may have changed.")
    return {"hitters": hitters, "errors": errors}


def _find_block_anchors(words: list) -> list[tuple[float, float]]:
    """Each 'vs.' + 'RHP' pair marks the top of a hitter block."""
    anchor_ys = sorted(
        w[1] for w in words
        if w[4] == "RHP" and any(
            v[4] == "vs." and abs(v[1] - w[1]) < _ROW_TOL for v in words
        )
    )
    blocks = []
    for i, y in enumerate(anchor_ys):
        y_next = anchor_ys[i + 1] if i + 1 < len(anchor_ys) else float("inf")
        blocks.append((y - _ROW_TOL, y_next - _ROW_TOL))
    return blocks


def _parse_hitter_block(block_words: list, page_number: int) -> dict | None:
    name_words = sorted(
        (w for w in block_words if w[0] < _NAME_MAX_X),
        key=lambda w: (w[1], w[0]),
    )
    header_text = " ".join(w[4] for w in name_words)
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

    table_words = [w for w in block_words if w[0] >= _NAME_MAX_X]
    rows = _group_rows(table_words)

    splits: dict[str, list[dict]] = {"vs. RHP": [], "vs. LHP": []}
    for row in rows:
        left = [w for w in row if w[0] < _SIDE_SPLIT_X]
        right = [w for w in row if w[0] >= _SIDE_SPLIT_X]
        for side, cells in (("vs. RHP", left), ("vs. LHP", right)):
            parsed = _parse_stat_row(cells)
            if parsed:
                splits[side].append(parsed)

    if not splits["vs. RHP"] and not splits["vs. LHP"]:
        return None

    return {
        "number": number,
        "name": name,
        "bats": bats,
        "team": team,
        "source_page": page_number,
        "splits": splits,
    }


def _group_rows(words: list) -> list[list]:
    """Group words into visual rows by y-position."""
    rows: list[tuple[float, list]] = []
    for w in sorted(words, key=lambda w: w[1]):
        for y, row in rows:
            if abs(w[1] - y) <= _ROW_TOL:
                row.append(w)
                break
        else:
            rows.append((w[1], [w]))
    return [sorted(row, key=lambda w: w[0]) for _, row in rows]


def _parse_stat_row(cells: list) -> dict | None:
    """Parse one side of a table row: [pitch, P, 9 stat cells]."""
    tokens = [w[4] for w in cells]
    if not tokens or tokens[0] not in PITCH_LABELS:
        return None
    if len(tokens) != 2 + len(STAT_COLUMNS):
        return None

    row: dict = {"Pitch": tokens[0]}
    row["P"] = _to_number(tokens[1], integer=True)
    for col, raw in zip(STAT_COLUMNS, tokens[2:]):
        row[col] = _to_number(raw)
    return row


def _to_number(raw: str, integer: bool = False):
    """Convert a cell to a number; '-' (missing) becomes None."""
    raw = raw.strip()
    if raw in {"-", ""}:
        return None
    try:
        if integer:
            return int(raw)
        if raw.endswith("%"):
            return float(raw[:-1])
        return float(raw)
    except ValueError:
        return None
