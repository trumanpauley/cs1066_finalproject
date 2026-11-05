"""Tests for the chatbot's retrieval and prompt building (no API key or network needed).

Run with:  python -m pytest tests/test_assistant.py -v
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from pitchiq.assistant import (
    NOTES_INLINE_CHARS,
    AnswerStream,
    estimate_cost,
    retrieve,
    system_blocks,
    user_turn,
)
from pitchiq.config import CHAT_EFFORT, CHAT_MODEL
from pitchiq.knowledge import Document, build_chunks
from pitchiq.knowledge.retrieval import BM25Index, find_hitters, find_teams, normalize

TEAMS = [
    {"id": 119, "name": "Los Angeles Dodgers", "abbreviation": "LAD", "nickname": "Dodgers", "location": "Los Angeles"},
    {"id": 108, "name": "Los Angeles Angels", "abbreviation": "LAA", "nickname": "Angels", "location": "Los Angeles"},
    {"id": 135, "name": "San Diego Padres", "abbreviation": "SD", "nickname": "Padres", "location": "San Diego"},
    {"id": 147, "name": "New York Yankees", "abbreviation": "NYY", "nickname": "Yankees", "location": "New York"},
]
HITTERS = [
    {"id": 1, "name": "Mookie Betts", "team": "LAD"},
    {"id": 2, "name": "Aaron Judge", "team": "NYY"},
    {"id": 3, "name": "José Ramírez", "team": "CLE"},
    {"id": 4, "name": "Ronald Acuña Jr.", "team": "ATL"},
    {"id": 5, "name": "Will Smith", "team": "LAD"},
    {"id": 6, "name": "Dominic Smith", "team": "SF"},
]


# --- entity lookup -------------------------------------------------------------------

@pytest.mark.parametrize("question,expected", [
    ("How should I pitch to the Dodgers?", ["Los Angeles Dodgers"]),
    ("game plan vs LAD", ["Los Angeles Dodgers"]),
    ("facing the los angeles dodgers tomorrow", ["Los Angeles Dodgers"]),
    ("Dodgers or Angels — who's tougher?", ["Los Angeles Dodgers", "Los Angeles Angels"]),
    ("what about the Yankees lineup", ["New York Yankees"]),
    ("I need some advice on my slider", []),
    ("Should I throw it sd or not", []),  # lowercase 'sd' is not the Padres
])
def test_find_teams(question, expected):
    assert [t["name"] for t in find_teams(question, TEAMS)] == expected


@pytest.mark.parametrize("question,expected", [
    ("Give me a plan for Aaron Judge.", [2]),
    ("How do I get Betts out?", [1]),                       # unique last name, capitalized
    ("he bets on fastballs", []),                           # lowercase word isn't a name
    ("plan for jose ramirez", [3]),                          # accents and case ignored
    ("What about Acuña?", [4]),                              # 'Jr.' suffix skipped
    ("How do I pitch Smith?", []),                           # two Smiths: ambiguous, skip
    ("How do I pitch Will Smith?", [5]),                     # full name resolves it
])
def test_find_hitters(question, expected):
    assert sorted(h["id"] for h in find_hitters(question, HITTERS)) == expected


def test_ambiguous_last_name_resolves_to_hitter_in_conversation():
    assert find_hitters("How do I pitch Smith?", HITTERS) == []
    assert [h["id"] for h in find_hitters("How do I pitch Smith?", HITTERS, prefer_ids={5, 1})] == [5]
    # still ambiguous if both Smiths were discussed
    assert find_hitters("How do I pitch Smith?", HITTERS, prefer_ids={5, 6}) == []


def test_normalize_strips_accents():
    assert normalize("José Ramírez") == "jose ramirez"


# --- BM25 ------------------------------------------------------------------------------

def test_bm25_ranks_the_relevant_chunk_first():
    docs = [
        Document("note:a", "note", "bullpen", "Bullpen plan: work on changeup grip and arm speed."),
        Document("note:b", "note", "coach", "Coach says elevate the four-seam fastball against lefties."),
        Document("note:c", "note", "travel", "Bus leaves at 3pm for the road trip."),
    ]
    hits = BM25Index(build_chunks(docs)).search("how should I use my fastball vs lefties", k=2)
    assert hits[0][0].doc_id == "note:b"
    assert all(c.doc_id != "note:c" for c, _ in hits)


def test_bm25_no_match_returns_nothing():
    docs = [Document("note:a", "note", "t", "changeup grip")]
    assert BM25Index(build_chunks(docs)).search("weather tomorrow") == []


# --- retrieve -----------------------------------------------------------------------------

def _hitter_doc(h):
    return Document(f"hitter:{h['id']}:2026:R", "hitter", f"{h['name']} — 2026 vs RHP", f"{h['name']} data")


ROSTERS = {119: [{"id": 1, "name": "Mookie Betts"}, {"id": 5, "name": "Will Smith"}]}


def _retrieve(question, **kw):
    return retrieve(question, teams=TEAMS, hitters=HITTERS, roster_for=lambda t: ROSTERS[t["id"]],
                    hitter_doc_for=_hitter_doc, note_docs=kw.pop("note_docs", []), **kw)


def test_team_question_pulls_the_roster():
    ctx = _retrieve("How should I pitch to the Dodgers?")
    assert [t["abbreviation"] for t in ctx.teams] == ["LAD"]
    assert [d.title for d in ctx.hitter_docs] == ["Mookie Betts — 2026 vs RHP", "Will Smith — 2026 vs RHP"]


def test_team_plus_named_hitter_has_no_duplicates():
    ctx = _retrieve("Dodgers, especially Mookie Betts")
    assert [h["id"] for h in ctx.hitters] == [1, 5]


def test_follow_up_does_not_resend_documents():
    first = _retrieve("How should I pitch to the Dodgers?")
    sent = {d.id for d in first.hitter_docs}
    again = _retrieve("And Betts again with two strikes?", already_sent=sent)
    assert again.hitters and again.hitter_docs == []


def test_failures_are_reported_not_raised():
    def broken(h):
        raise ValueError("no 2026 pitches")
    ctx = retrieve("Plan for Aaron Judge", teams=TEAMS, hitters=HITTERS, roster_for=lambda t: [],
                   hitter_doc_for=broken, note_docs=[])
    assert ctx.failed == ["Aaron Judge (no 2026 pitches)"]


def test_short_notes_sent_whole_long_notes_searched():
    short = [Document("note:a", "note", "coach", "Elevate fastballs."),
             Document("note:b", "note", "bullpen", "Changeup grip.")]
    assert {c.doc_id for c in _retrieve("anything", note_docs=short).note_chunks} == {"note:a", "note:b"}

    long_text = ("Travel and schedule details. " * 300) + "\n\nVersus lefties, elevate the fastball."
    long = [Document("note:big", "note", "season notes", long_text)]
    assert len(long_text) > NOTES_INLINE_CHARS
    chunks = _retrieve("fastball plan vs lefties", note_docs=long).note_chunks
    assert 0 < len(chunks) <= 4
    assert any("elevate the fastball" in c.text for c in chunks)


# --- prompt building ------------------------------------------------------------------------

def test_system_blocks_cache_instructions_and_profile():
    blocks = system_blocks([Document("pitch:Sweeper", "pitch", "T — Sweeper", "sweeper text")])
    assert len(blocks) == 1 and blocks[0]["cache_control"] == {"type": "ephemeral"}
    text = blocks[0]["text"]
    assert text.index("PitchIQ") < text.index("<pitcher_profile>") < text.index("sweeper text")


def test_user_turn_puts_data_before_question_and_sets_depth():
    ctx = _retrieve("How should I pitch to the Dodgers?")
    text = user_turn("How should I pitch to the Dodgers?", ctx, "Quick")
    assert text.index("<scouting_data>") < text.index("QUICK") < text.index("How should I pitch")
    assert "Mookie Betts data" in text


def test_user_turn_without_new_data_is_just_the_question():
    from pitchiq.assistant import RetrievedContext
    text = user_turn("What about with runners on?", RetrievedContext(), "Standard")
    assert "<scouting_data>" not in text and text.endswith("What about with runners on?")


# --- streaming wrapper (fake client, no network) ----------------------------------------------

class _FakeStream:
    def __init__(self, chunks, final):
        self.text_stream, self._final = iter(chunks), final

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._final


def test_answer_stream_sends_expected_request_and_keeps_final_message():
    calls = {}
    final = SimpleNamespace(stop_reason="end_turn", content=["block"])

    def stream(**kwargs):
        calls.update(kwargs)
        return _FakeStream(["Start ", "him away."], final)

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream)))
    s = AnswerStream(client, system=[{"type": "text", "text": "sys"}], messages=[{"role": "user", "content": "q"}])
    assert "".join(s) == "Start him away."
    assert s.message is final
    assert calls["model"] == CHAT_MODEL and calls["output_config"] == {"effort": CHAT_EFFORT}
    assert calls["fallbacks"] == "default" and calls["betas"] == ["server-side-fallback-2026-07-01"]
    assert "thinking" not in calls and "temperature" not in calls


def test_estimate_cost():
    usage = SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000,
                            cache_creation_input_tokens=0, cache_read_input_tokens=1_000_000)
    assert estimate_cost(usage) == pytest.approx(4.00 + 2.00 + 0.20)
