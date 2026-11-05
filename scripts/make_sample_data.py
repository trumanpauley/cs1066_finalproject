"""Generate fictional test files for PitchIQ: two outing reports + a notes PDF.

The pitcher, Casey Marlow (LHP), is made up. The outing reports use the same
table layout as the pitching process reports the app parses, so they exercise
the real upload path without any confidential team data. Every page is
labeled as sample data.

Run:  python scripts/make_sample_data.py      -> writes samples/
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parents[1] / "samples"
PITCHER = "Casey Marlow"
LABEL = "SAMPLE DATA - fictional pitcher generated for PitchIQ testing"

# Columns: usage, Usg vL, P2K vL, 2K vL, Usg vR, P2K vR, 2K vR, P2K IZ, code, velo,
#          RelS, RelH, Ext, Spin Eff, IVB, HB.  Results: whiffs/swings, strikes, FPK/first pitches.
OUTINGS = [
    {
        "file": "sample_outing_2026-07-12.pdf",
        "date": "07/12/2026",
        "race": ("62% (13/21)", "60%", "64%"),
        "fps": ("57% (13/23)", "58%", "61%"),
        "rows": [
            ("38 (42%)", "48%", "50%", "40%", "39%", "41%", "33%", "52%", "FF", "91-95 (93)",
             "1'9\"", "6'1\"", "6'4\"", "94%", "17.2", "11.8", (5, 19), 24, (8, 12)),
            ("22 (24%)", "30%", "32%", "20%", "21%", "23%", "14%", "58%", "SI", "90-93 (91)",
             "1'10\"", "6'0\"", "6'3\"", "91%", "8.4", "16.1", (1, 9), 14, (4, 6)),
            ("17 (19%)", "6%", "4%", "10%", "26%", "22%", "35%", "41%", "CH", "83-86 (85)",
             "1'9\"", "6'0\"", "6'4\"", "88%", "6.0", "14.5", (7, 13), 11, (1, 2)),
            ("13 (15%)", "16%", "14%", "30%", "14%", "14%", "18%", "38%", "CB", "76-79 (78)",
             "1'8\"", "6'1\"", "6'2\"", "", "-12.4", "-7.9", (4, 8), 8, (0, 3)),
        ],
    },
    {
        "file": "sample_outing_2026-07-24.pdf",
        "date": "07/24/2026",
        "race": ("71% (15/21)", "61%", "64%"),
        "fps": ("65% (15/23)", "59%", "61%"),
        "rows": [
            ("35 (40%)", "44%", "47%", "38%", "37%", "40%", "30%", "55%", "FF", "92-95 (94)",
             "1'9\"", "6'1\"", "6'5\"", "95%", "17.8", "11.2", (6, 17), 23, (7, 10)),
            ("19 (22%)", "29%", "31%", "18%", "19%", "21%", "12%", "60%", "SI", "90-93 (92)",
             "1'10\"", "6'0\"", "6'3\"", "90%", "7.9", "16.6", (1, 8), 13, (5, 7)),
            ("19 (22%)", "8%", "6%", "12%", "28%", "24%", "38%", "44%", "CH", "84-86 (85)",
             "1'9\"", "6'0\"", "6'4\"", "87%", "5.4", "15.0", (8, 14), 13, (2, 3)),
            ("14 (16%)", "19%", "16%", "32%", "16%", "15%", "20%", "36%", "CB", "77-80 (78)",
             "1'8\"", "6'1\"", "6'3\"", "", "-13.1", "-8.3", (5, 9), 9, (1, 3)),
        ],
    },
]

HEADERS = ["Usage", "Usg vL", "P2K vL", "2K vL", "Usg vR", "P2K vR", "2K vR", "P2K IZ",
           "Pitch Type", "Velo", "RelS", "RelH", "Ext", "Spin Eff", "IVB", "HB"]
COL_X = [36, 80, 113, 146, 179, 212, 245, 278, 314, 352, 410, 443, 476, 509, 545, 575]

NOTES = f"""{PITCHER} - Pitching Notes (LHP)
{LABEL}

Pitching identity
I'm a left-handed starter who lives off fastball ride up in the zone and a changeup that dies at the plate. I want to get ahead with the fastball and finish righties with the changeup and lefties with the curveball.

4-seam fastball
How I throw it: 92-95 with good ride. Best at the top of the zone; when it runs back over the middle it gets hit hard. I can throw it for a strike in any count.
Vs righties: up and in to tie them up, then changeup away off the same tunnel.
Vs lefties: up and away, climb the ladder with two strikes.

Sinker
How I throw it: two-seam grip, runs arm side. Mostly a ground-ball pitch to lefties when I need a double play. I don't trust it to righties - it runs back into their bat.

Changeup
How I throw it: circle change, same arm speed as the heater. My best swing-and-miss pitch to righties, down and away. Confidence: best pitch. I will throw it in any count to a righty, including 3-1.

Curveball
How I throw it: big 12-6 shape, 77-79. My put-away pitch to lefties: it breaks down and away from them. I struggle to land it for a called strike early in counts.

Coach's notes (bullpen, 07/20/2026)
- Elevate the 4-seam more with two strikes; we were leaving it thigh-high.
- Throw the curveball more to lefties early in counts, even if it's a ball - it changes their eye level.
- Against aggressive first-pitch swingers, start them with the changeup instead of the fastball.
"""


def _page_label(page: pymupdf.Page) -> None:
    page.insert_text((36, 770), LABEL, fontsize=8, color=(0.5, 0.5, 0.5))


def make_outing(outing: dict) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((180, 50), f"{PITCHER} Pitching Report", fontsize=14)
    page.insert_text((270, 66), outing["date"], fontsize=10)

    # Race to 2K / First-Pitch Strikes: one cell per line, as the parser expects.
    for x0, title, values in ((60, "Race to 2K", outing["race"]), (330, "First-Pitch Strikes", outing["fps"])):
        page.insert_text((x0 + 60, 100), title, fontsize=10)
        for i, cell in enumerate(("Range", "2026", "MLB")):
            page.insert_text((x0 + i * 80, 116), cell, fontsize=8)
        for i, cell in enumerate(values):
            page.insert_text((x0 + i * 80, 130), cell, fontsize=8)

    y = 170
    for x, head in zip(COL_X, HEADERS):
        page.insert_text((x, y), head, fontsize=6)
    for row in outing["rows"]:
        y += 16
        for x, cell in zip(COL_X, row[:16]):
            if cell:
                page.insert_text((x, y), cell, fontsize=7)
    _page_label(page)

    # Page 2: per-pitch results under each pitch code.
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 50), f"{PITCHER} Pitching Report - Execution", fontsize=12)
    y = 90
    for row in outing["rows"]:
        code, (whiffs, swings), strikes, (fpk, firsts) = row[8], row[16], row[17], row[18]
        usage = int(row[0].split()[0])
        for i, line in enumerate((code, f"Whiffs: {whiffs}/{swings}", f"Strikes: {strikes}/{usage}",
                                  f"FPK: {fpk}/{firsts}")):
            page.insert_text((280, y + i * 14), line, fontsize=9)
        y += 80
    _page_label(page)
    data = doc.tobytes()
    doc.close()
    return data


def make_notes() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(pymupdf.Rect(48, 48, 564, 744), NOTES, fontsize=10)
    _page_label(page)
    data = doc.tobytes()
    doc.close()
    return data


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for outing in OUTINGS:
        (OUT / outing["file"]).write_bytes(make_outing(outing))
    (OUT / "sample_pitching_notes.pdf").write_bytes(make_notes())
    print(f"Wrote {len(OUTINGS)} outing reports and a notes PDF to {OUT}")


if __name__ == "__main__":
    main()
