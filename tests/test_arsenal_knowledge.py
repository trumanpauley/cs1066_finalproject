"""Tests for combining outings, the saved profile, and the RAG knowledge documents.

Run with:  python -m pytest tests/test_arsenal_knowledge.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pitchiq.arsenal import combine_outings, merge_into_arsenal, outing_sort_key
from pitchiq.knowledge import build_chunks, chunk_text, pitcher_documents
from pitchiq.profile_store import content_id, delete_upload, load_profile, save_profile, save_upload

REPORT_DIR = Path(__file__).parent.parent / "journals" / "Scouting_Reports"


def _pitch(name, code, count, velo=(90, 94, 92), whiffs=0, swings=0, strikes=0, fpk=0, firsts=0,
           ivb=10.0, hb=0.0, usage_vl=None, usage_vr=None):
    return {"code": code, "name": name, "usage_count": count, "velo_low": velo[0], "velo_high": velo[1],
            "velo_avg": velo[2], "ivb": ivb, "hb": hb, "whiffs": whiffs, "swings": swings,
            "strikes": strikes, "fpk": fpk, "first_pitches": firsts,
            "usage_vl": usage_vl, "usage_vr": usage_vr}


OUTING_A = {  # older outing, 30 pitches
    "id": "a", "filename": "a.pdf", "date_range": "08/04/2026 - 08/09/2026",
    "race_to_2k": "50% (8/16)", "race_to_2k_season": "60%", "race_to_2k_mlb": "64%",
    "first_pitch_strikes": "53% (10/19)", "first_pitch_strikes_season": "55%", "first_pitch_strikes_mlb": "61%",
    "pitches": [
        _pitch("Fastball (4-Seam)", "FF", 20, (90, 93, 91), whiffs=2, swings=10, strikes=12, fpk=3, firsts=5,
               ivb=17.0, usage_vl=40, usage_vr=60),
        _pitch("Sweeper", "SW", 10, (80, 83, 82), whiffs=4, swings=6, strikes=7, fpk=1, firsts=1,
               ivb=-4.0, hb=-10.0, usage_vl=60, usage_vr=40),
    ],
}
OUTING_B = {  # newer outing, 10 pitches, adds a cutter
    "id": "b", "filename": "b.pdf", "date_range": "09/02/2026",
    "race_to_2k": "70% (7/10)", "race_to_2k_season": "61%", "race_to_2k_mlb": "64%",
    "first_pitch_strikes": "60% (6/10)", "first_pitch_strikes_season": "56%", "first_pitch_strikes_mlb": "61%",
    "pitches": [
        _pitch("Fastball (4-Seam)", "FF", 5, (91, 95, 93), whiffs=1, swings=2, strikes=4, fpk=2, firsts=3,
               ivb=19.0, usage_vl=50, usage_vr=50),
        _pitch("Cutter", "FC", 5, (88, 90, 89), whiffs=0, swings=3, strikes=3, usage_vl=50, usage_vr=50),
    ],
}


# --- combine_outings -------------------------------------------------------------

def test_counts_are_summed_and_rates_are_exact():
    c = combine_outings([OUTING_B, OUTING_A])
    ff = c["pitches"]["Fastball (4-Seam)"]
    assert ff["pitches"] == 25 and ff["outings"] == 2
    assert ff["whiff_pct"] == pytest.approx(100 * 3 / 12, abs=0.1)
    assert ff["strike_pct"] == pytest.approx(100 * 16 / 25, abs=0.1)
    assert ff["fpk_pct"] == pytest.approx(100 * 5 / 8, abs=0.1)
    assert (ff["velo_low"], ff["velo_high"]) == (90, 95)
    # usage share of all 40 pitches
    assert ff["usage_pct"] == pytest.approx(62.5)
    assert c["pitches"]["Cutter"]["usage_pct"] == pytest.approx(12.5)


def test_averages_are_weighted():
    ff = combine_outings([OUTING_A, OUTING_B])["pitches"]["Fastball (4-Seam)"]
    # velo/movement weighted by pitches thrown (20 and 5)
    assert ff["velo_avg"] == pytest.approx((91 * 20 + 93 * 5) / 25, abs=0.1)
    assert ff["ivb"] == pytest.approx((17 * 20 + 19 * 5) / 25, abs=0.1)
    # usage splits weighted by each outing's total pitches (30 and 10)
    assert ff["usage_vl"] == pytest.approx((40 * 30 + 50 * 10) / 40, abs=0.1)


def test_summary_combines_counts_and_uses_latest_season_line():
    s = combine_outings([OUTING_B, OUTING_A])["summary"]
    assert s["race_to_2k"]["made"] == 15 and s["race_to_2k"]["total"] == 26
    assert s["first_pitch_strikes"]["pct"] == pytest.approx(100 * 16 / 29, abs=0.1)
    assert s["race_to_2k"]["season"] == "61%"  # from the newest outing (09/02)
    assert (s["first_date"], s["last_date"]) == ("08/04/2026 - 08/09/2026", "09/02/2026")


def test_outing_sort_key_uses_last_date():
    assert outing_sort_key(OUTING_A) < outing_sort_key(OUTING_B)
    assert sorted([OUTING_B, OUTING_A], key=outing_sort_key)[0]["id"] == "a"


# --- merge_into_arsenal ------------------------------------------------------------

def test_merge_keeps_what_the_pitcher_wrote():
    arsenal = [
        {"pitch": "Sweeper", "velo_low": 70, "velo_high": 71, "usage_pct": 5, "ivb": 0, "hb": 0,
         "notes": "Start it at the hip.", "plan_vs_rhh": "Back door", "best_counts": ["Two strikes"],
         "confidence": "Best pitch"},
        {"pitch": "ChangeUp", "velo_low": 84, "velo_high": 86, "usage_pct": 5, "ivb": 6, "hb": 12,
         "notes": "Still learning it", "source": "manual"},
    ]
    merged = merge_into_arsenal(arsenal, combine_outings([OUTING_A, OUTING_B]))
    names = [p["pitch"] for p in merged]
    assert names == ["Fastball (4-Seam)", "Sweeper", "Cutter", "ChangeUp"]  # most used first, manual last
    sw = merged[1]
    assert (sw["notes"], sw["plan_vs_rhh"], sw["best_counts"], sw["confidence"]) == \
           ("Start it at the hip.", "Back door", ["Two strikes"], "Best pitch")
    assert (sw["velo_low"], sw["velo_high"]) == (80, 83)      # numbers come from the reports
    assert merged[3]["notes"] == "Still learning it"            # hand-added pitch untouched


def test_deleting_all_reports_keeps_pitches_but_drops_stale_stats():
    merged = merge_into_arsenal([], combine_outings([OUTING_A]))
    merged[0]["notes"] = "My heater"
    after = merge_into_arsenal(merged, combine_outings([]))
    assert [p["pitch"] for p in after] == ["Fastball (4-Seam)", "Sweeper"]
    assert after[0]["notes"] == "My heater"
    assert "stats" not in after[0]


# --- profile_store --------------------------------------------------------------------

def test_profile_round_trip_and_uploads(tmp_path):
    profile = {"pitcher_name": "Test Pitcher", "throwing_hand": "Right (RHP)",
               "arsenal": [{"pitch": "Sweeper", "notes": "hip"}], "approach": "Attack",
               "outings": [OUTING_A], "notes_docs": [], "not_a_profile_key": "ignored"}
    save_profile(profile, base=tmp_path)
    loaded = load_profile(base=tmp_path)
    assert loaded["pitcher_name"] == "Test Pitcher"
    assert loaded["outings"][0]["date_range"] == OUTING_A["date_range"]
    assert "not_a_profile_key" not in loaded

    fid = content_id(b"pdf bytes")
    assert fid == content_id(b"pdf bytes") != content_id(b"other bytes")
    path = save_upload(fid, "report.pdf", b"pdf bytes", base=tmp_path)
    assert path.read_bytes() == b"pdf bytes"
    delete_upload(fid, base=tmp_path)
    assert not path.exists()


def test_load_profile_missing_file(tmp_path):
    assert load_profile(base=tmp_path / "nothing-here") == {}


# --- knowledge documents ----------------------------------------------------------------

def _profile():
    arsenal = merge_into_arsenal([], combine_outings([OUTING_A, OUTING_B]))
    arsenal[1]["notes"] = "Start it at the hip of a righty."
    arsenal[1]["plan_vs_lhh"] = "Back-foot with two strikes."
    return {"pitcher_name": "Test Pitcher", "throwing_hand": "Right (RHP)", "arsenal": arsenal,
            "strengths": "Sweeper", "weaknesses": "", "preferences": "", "approach": "Get ahead early.",
            "outings": [OUTING_A, OUTING_B],
            "notes_docs": [{"id": "n1", "filename": "coach.txt", "text": "Elevate fastballs.", "added": "2026-11-05"}]}


def test_pitcher_documents_cover_everything_with_stable_ids():
    docs = pitcher_documents(_profile())
    ids = [d.id for d in docs]
    assert ids == ["pitcher:overview", "pitch:Fastball (4-Seam)", "pitch:Sweeper", "pitch:Cutter",
                   "outing:a", "outing:b", "note:n1"]
    sweeper = docs[2].text
    # Self-contained: names the pitcher and pitch, includes report numbers and the pitcher's words.
    assert "Test Pitcher's Sweeper" in sweeper
    assert "whiff rate 67%" in sweeper
    assert "How I throw it: Start it at the hip of a righty." in sweeper
    assert "Plan vs left-handed hitters: Back-foot with two strikes." in sweeper
    overview = docs[0].text
    assert "How I attack hitters (in Test Pitcher's words): Get ahead early." in overview
    assert "Race to 2 strikes: 58% (15/26)" in overview
    assert docs[2].metadata == {"pitcher": "Test Pitcher", "hand": "Right (RHP)", "pitch": "Sweeper"}


def test_empty_profile_still_builds_an_overview():
    docs = pitcher_documents({})
    assert [d.kind for d in docs] == ["pitcher_overview"]


def test_chunk_text_respects_size_and_overlaps():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(10))
    chunks = chunk_text(text, max_chars=400, overlap=80)
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)
    assert all(f"Paragraph {i}." in text for i in range(10))
    # every paragraph label survives somewhere
    assert all(any(f"Paragraph {i}." in c for c in chunks) for i in range(10))
    assert chunk_text("short") == ["short"]
    assert chunk_text("   ") == []


def test_build_chunks_ids_and_metadata():
    docs = pitcher_documents(_profile())
    chunks = build_chunks(docs, max_chars=200)
    assert len(chunks) > len(docs)  # long docs were split
    assert all(c.id.startswith(c.doc_id + "#") for c in chunks)
    sweeper_chunks = [c for c in chunks if c.doc_id == "pitch:Sweeper"]
    assert all(c.metadata["pitch"] == "Sweeper" for c in sweeper_chunks)


# --- real reports (skipped without the confidential PDFs) ---------------------------------

def test_three_real_outings_combine():
    paths = [REPORT_DIR / f"document ({n}).pdf" for n in (4, 5, 6)]
    if not all(p.exists() for p in paths):
        pytest.skip("Reference PDFs not available")
    from pitchiq.extraction import extract_report
    outings = [{**extract_report(p.read_bytes(), p.name), "id": p.stem} for p in paths]
    c = combine_outings(outings)
    total = sum(p["usage_count"] for o in outings for p in o["pitches"])
    assert c["summary"]["pitches"] == total
    assert c["summary"]["race_to_2k"]["total"] == 19 + 15 + 16
    assert set(c["pitches"]) == {"Fastball (4-Seam)", "Sweeper", "Cutter", "Slider"}
    assert sum(s["usage_pct"] for s in c["pitches"].values()) == pytest.approx(100, abs=0.5)
