"""Tests comparing extracted values with the original reference PDFs.

The reference PDFs are confidential scouting reports kept in
journals/Scouting_Reports/ (gitignored — never committed). Tests skip
automatically when the files are not present, so CI without the PDFs
still passes.

Run with:  python -m pytest tests/ -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pitchiq.extraction import extract_report

REPORT_DIR = Path(__file__).parent.parent / "journals" / "Scouting_Reports"


def _load(name: str) -> dict:
    path = REPORT_DIR / name
    if not path.exists():
        pytest.skip(f"Reference PDF not available: {name}")
    return extract_report(path.read_bytes(), name)


# ---------------------------------------------------------------------------
# Pitcher process reports (Sockeye format)
# ---------------------------------------------------------------------------

class TestPitcherReport:
    def test_doc6_metadata(self):
        r = _load("document (6).pdf")
        assert r["report_type"] == "pitcher_report"
        assert r["errors"] == []
        assert r["pitcher_name"] == "Truman Pauley"
        assert r["date_range"] == "08/04/2026 - 08/09/2026"
        assert r["race_to_2k"] == "50% (8/16)"
        assert r["first_pitch_strikes"] == "53% (10/19)"

    def test_doc6_pitches_match_pdf_table(self):
        r = _load("document (6).pdf")
        rows = {p["code"]: p for p in r["pitches"]}
        assert list(rows) == ["FF", "FC", "SW", "SL"]

        ff = rows["FF"]
        assert (ff["velo_low"], ff["velo_high"], ff["velo_avg"]) == (88, 95, 92)
        assert (ff["usage_count"], ff["usage_pct"]) == (33, 43)
        assert (ff["ivb"], ff["hb"]) == (16.3, 5.3)

        fc = rows["FC"]
        assert (fc["velo_low"], fc["velo_high"], fc["velo_avg"]) == (87, 92, 90)
        assert (fc["usage_count"], fc["usage_pct"]) == (27, 35)
        assert (fc["ivb"], fc["hb"]) == (9.0, -2.9)

        sw = rows["SW"]
        assert (sw["velo_low"], sw["velo_high"], sw["velo_avg"]) == (81, 85, 83)
        assert (sw["usage_count"], sw["usage_pct"]) == (10, 13)
        assert (sw["ivb"], sw["hb"]) == (-6.5, -13.3)

        sl = rows["SL"]
        assert (sl["velo_low"], sl["velo_high"], sl["velo_avg"]) == (85, 88, 86)
        assert (sl["usage_count"], sl["usage_pct"]) == (7, 9)
        assert (sl["ivb"], sl["hb"]) == (-0.3, -0.8)

    def test_doc6_missing_spin_eff_preserved(self):
        r = _load("document (6).pdf")
        # The Spin Eff column is empty in this report — it must stay missing.
        assert all(p["spin_eff"] is None for p in r["pitches"])

    def test_other_pitcher_reports_parse(self):
        for name in ("document (4).pdf", "document (5).pdf"):
            r = _load(name)
            assert r["report_type"] == "pitcher_report"
            assert r["pitcher_name"] == "Truman Pauley"
            assert len(r["pitches"]) == 4
            assert r["errors"] == []

    def test_doc4_single_date_and_values(self):
        r = _load("document (4).pdf")
        assert r["date_range"] == "09/02/2026"
        sw = {p["code"]: p for p in r["pitches"]}["SW"]
        assert (sw["usage_count"], sw["usage_pct"]) == (32, 38)
        assert (sw["ivb"], sw["hb"]) == (-4.1, -9.2)

    def test_doc5_spin_efficiency_extracted(self):
        r = _load("document (5).pdf")
        rows = {p["code"]: p for p in r["pitches"]}
        # Spin Eff appears as "87%" for FF in this report.
        assert rows["FF"]["spin_eff"] == 87.0
        assert (rows["FF"]["ivb"], rows["FF"]["hb"]) == (17.4, 4.5)
        assert rows["SW"]["spin_eff"] == 38.0


# ---------------------------------------------------------------------------
# Opponent statistical reports (TruMedia grid)
# ---------------------------------------------------------------------------

class TestOpponentStats:
    def test_doc2_hitter_roster(self):
        r = _load("document (2).pdf")
        assert r["report_type"] == "opponent_stats"
        assert r["errors"] == []
        roster = [(h["number"], h["name"], h["bats"]) for h in r["hitters"]]
        assert len(roster) == 14
        assert roster[0] == (8, "Ty Southisene", "R")
        assert (40, "Josiah Hartshorn", "S") in roster
        assert (25, "Alexey Lumpuy", "L") in roster
        assert (32, "Derniche Valdez", "R") in roster

    def test_doc2_southisene_vs_rhp_values(self):
        r = _load("document (2).pdf")
        hitter = r["hitters"][0]
        assert hitter["source_page"] == 1
        rows = {row["Pitch"]: row for row in hitter["splits"]["vs. RHP"]}

        # Values transcribed from page 1 of the PDF.
        assert rows["Total"]["P"] == 1427
        assert rows["Total"]["FPSwing%"] == 19.3
        assert rows["Total"]["wOBA"] == 0.321

        fb = rows["Fastball"]
        assert fb["P"] == 671
        assert fb["FPSwing%"] == 23.3
        assert fb["InZoneWhiff%"] == 7.5
        assert fb["AVG"] == 0.306
        assert fb["ISO"] == 0.048
        assert fb["wOBA"] == 0.391

    def test_doc2_missing_values_and_sample_sizes_preserved(self):
        r = _load("document (2).pdf")
        hitter = r["hitters"][0]
        cutter_lhp = {
            row["Pitch"]: row for row in hitter["splits"]["vs. LHP"]
        }["Cutter"]
        # P=1 sample with '-' in most cells: sample size kept, missing -> None.
        assert cutter_lhp["P"] == 1
        assert cutter_lhp["FPSwing%"] is None
        assert cutter_lhp["AVG"] is None
        assert cutter_lhp["wOBA"] is None
        assert cutter_lhp["2K-Ch%"] == 0.0  # the one populated cell

    def test_doc2_every_hitter_has_full_rhp_table(self):
        r = _load("document (2).pdf")
        for h in r["hitters"]:
            pitches = [row["Pitch"] for row in h["splits"]["vs. RHP"]]
            assert pitches[0] == "Total", h["name"]
            assert len(pitches) >= 2, h["name"]


# ---------------------------------------------------------------------------
# Opponent heatmap reports
# ---------------------------------------------------------------------------

class TestHeatmapReport:
    def test_doc1_entries(self):
        r = _load("document (1).pdf")
        assert r["report_type"] == "opponent_heatmap"
        assert r["errors"] == []
        assert len(r["entries"]) == 28

        first = r["entries"][0]
        assert (first["number"], first["name"], first["bats"]) == (8, "Ty Southisene", "R")
        assert first["pitcher_hand"] == "RHP"
        assert first["page_number"] == 1
        assert first["data_pulled"] == "4/16/2026"
        assert "Fastball" in first["pitch_types"]

        second = r["entries"][1]
        assert second["name"] == "Ty Southisene"
        assert second["pitcher_hand"] == "LHP"
        assert second["page_number"] == 2

    def test_doc1_handedness_split_pairs(self):
        r = _load("document (1).pdf")
        # Pages alternate RHP/LHP for each hitter.
        hands = [e["pitcher_hand"] for e in r["entries"]]
        assert hands == ["RHP", "LHP"] * 14

    def test_doc1_header_variant_name_then_bats(self):
        # Page 3 splits the header as 'Hartshorn (S)' / 'Pelicans'.
        r = _load("document (1).pdf")
        page3 = next(e for e in r["entries"] if e["page_number"] == 3)
        assert (page3["number"], page3["name"], page3["bats"]) == (40, "Josiah Hartshorn", "S")

    def test_doc3_parses(self):
        r = _load("document (3).pdf")
        assert r["report_type"] == "opponent_heatmap"
        assert len(r["entries"]) == 28
        assert r["errors"] == []


# ---------------------------------------------------------------------------
# Detection / robustness
# ---------------------------------------------------------------------------

class TestDetection:
    def test_unreadable_bytes_reported_as_error(self):
        r = extract_report(b"not a pdf", "garbage.pdf")
        assert r["report_type"] == "unknown"
        assert r["errors"]

    def test_each_reference_pdf_detected_correctly(self):
        expected = {
            "document (1).pdf": "opponent_heatmap",
            "document (2).pdf": "opponent_stats",
            "document (3).pdf": "opponent_heatmap",
            "document (4).pdf": "pitcher_report",
            "document (5).pdf": "pitcher_report",
            "document (6).pdf": "pitcher_report",
        }
        for name, rtype in expected.items():
            assert _load(name)["report_type"] == rtype, name
