"""Turn the pitcher profile and hitter data into retrievable text documents.

Each document is written so it makes sense on its own when retrieved (it
names the pitcher/hitter and the pitch), because a retriever returns
chunks without their surroundings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pitchiq.arsenal import combine_outings, outing_sort_key

MAX_CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150


@dataclass
class Document:
    id: str          # stable: "pitch:Sweeper", "outing:<file id>", "hitter:661388:2026:R"
    kind: str        # pitcher_overview | pitch | outing | note | hitter
    title: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    id: str          # "<doc id>#<n>"
    doc_id: str
    kind: str
    title: str
    text: str
    metadata: dict = field(default_factory=dict)


# --- Chunking -------------------------------------------------------------------

def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split on paragraphs, then sentences, packing pieces up to `max_chars`.

    Consecutive chunks share up to `overlap` characters so a fact split across a
    boundary is still retrievable.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    pieces: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if len(para) <= max_chars:
            pieces.append(para)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", para)
        for s in sentences:  # a single huge "sentence" is hard-split
            pieces.extend(s[i:i + max_chars] for i in range(0, len(s), max_chars))

    chunks, current = [], ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= max_chars:
            current = candidate
            continue
        chunks.append(current)
        tail = current[-overlap:] if overlap else ""
        tail = tail[tail.find(" ") + 1:] if " " in tail else tail  # start on a word
        current = f"{tail} {piece}".strip() if len(tail) + len(piece) < max_chars else piece
    if current:
        chunks.append(current)
    return chunks


def build_chunks(documents: list[Document], max_chars: int = MAX_CHUNK_CHARS) -> list[Chunk]:
    chunks = []
    for doc in documents:
        for n, text in enumerate(chunk_text(doc.text, max_chars)):
            chunks.append(Chunk(id=f"{doc.id}#{n}", doc_id=doc.id, kind=doc.kind,
                                title=doc.title, text=text, metadata=dict(doc.metadata)))
    return chunks


# --- Pitcher documents ------------------------------------------------------------

def _num(v, suffix="", digits=0) -> str:
    if v is None:
        return "n/a"
    text = f"{v:.{digits}f}"
    return f"{text.lstrip('-') if float(text) == 0 else text}{suffix}"  # no "-0.0"


def _inches(v) -> str:
    if v is None:
        return "n/a"
    feet, inches = divmod(round(v), 12)
    return f"{feet}'{inches}\""


def pitcher_documents(profile: dict) -> list[Document]:
    """All documents about the pitcher: overview, each pitch, each outing, each notes file."""
    name = profile.get("pitcher_name") or "The pitcher"
    hand = profile.get("throwing_hand") or "unknown hand"
    arsenal = profile.get("arsenal") or []
    outings = sorted(profile.get("outings") or [], key=outing_sort_key)
    meta = {"pitcher": name, "hand": hand}
    docs = [_overview_doc(profile, name, hand, arsenal, outings, meta)]
    docs += [_pitch_doc(p, name, hand, meta) for p in arsenal]
    docs += [_outing_doc(o, name, meta) for o in outings]
    for note in profile.get("notes_docs") or []:
        docs.append(Document(
            id=f"note:{note['id']}", kind="note",
            title=f"{name} — notes: {note['filename']}",
            text=f"{name}'s uploaded notes ({note['filename']}):\n\n{note['text']}",
            metadata={**meta, "source": note["filename"]},
        ))
    return docs


def _overview_doc(profile, name, hand, arsenal, outings, meta) -> Document:
    lines = [f"Pitcher overview: {name}, {hand}."]
    if arsenal:
        mix = ", ".join(f"{p['pitch']} {p.get('usage_pct', 0)}% "
                        f"({p.get('velo_low')}-{p.get('velo_high')} mph)" for p in arsenal)
        lines.append(f"Pitch mix: {mix}.")
    if outings:
        s = combine_outings(outings)["summary"]
        lines.append(f"Reports uploaded: {s['outings']} outings ({s['first_date']} to {s['last_date']}), "
                     f"{s['pitches']} pitches.")
        for key, label in (("race_to_2k", "Race to 2 strikes"), ("first_pitch_strikes", "First-pitch strikes")):
            v = s[key]
            if v["total"]:
                lines.append(f"{label}: {v['pct']:.0f}% ({v['made']}/{v['total']}) across these outings; "
                             f"season {v['season'] or 'n/a'}, MLB average {v['mlb'] or 'n/a'}.")
    for key, label in (("strengths", "Strengths"), ("weaknesses", "Weaknesses"),
                       ("preferences", "Preferences"), ("approach", "How I attack hitters")):
        if (profile.get(key) or "").strip():
            lines.append(f"\n{label} (in {name}'s words): {profile[key].strip()}")
    return Document(id="pitcher:overview", kind="pitcher_overview",
                    title=f"{name} — overview", text="\n".join(lines), metadata=meta)


def _pitch_doc(p: dict, name: str, hand: str, meta: dict) -> Document:
    pitch = p["pitch"]
    lines = [f"{name}'s {pitch} ({hand}): {p.get('velo_low')}-{p.get('velo_high')} mph"
             + (f", averaging {p['velo_avg']:.0f} mph" if p.get("velo_avg") else "")
             + f", thrown {p.get('usage_pct', 0)}% of the time. "
             f"Movement: {_num(p.get('ivb'), ' in', 1)} induced vertical break, "
             f"{_num(p.get('hb'), ' in', 1)} horizontal break."]
    s = p.get("stats")
    if s:
        lines.append(
            f"From {s['outings']} uploaded outing(s), {s['pitches']} pitches: "
            f"whiff rate {_num(s['whiff_pct'], '%')} ({s['swings']} swings), "
            f"strike rate {_num(s['strike_pct'], '%')}, "
            f"first-pitch strike rate {_num(s['fpk_pct'], '%')} ({s['first_pitches']} first pitches), "
            f"in the zone {_num(s['in_zone_p2k'], '%')} of the time before two strikes.")
        lines.append(
            f"Share of all pitches vs left-handed hitters: {_num(s['usage_vl'], '%')} "
            f"(with two strikes {_num(s['usage_2k_vl'], '%')}); vs right-handed hitters: "
            f"{_num(s['usage_vr'], '%')} (with two strikes {_num(s['usage_2k_vr'], '%')}).")
        lines.append(f"Release: side {_inches(s['release_side_in'])}, height {_inches(s['release_height_in'])}, "
                     f"extension {_inches(s['extension_in'])}.")
    qual = []
    if p.get("notes"):
        qual.append(f"How I throw it: {p['notes']}")
    if p.get("plan_vs_rhh"):
        qual.append(f"Plan vs right-handed hitters: {p['plan_vs_rhh']}")
    if p.get("plan_vs_lhh"):
        qual.append(f"Plan vs left-handed hitters: {p['plan_vs_lhh']}")
    if p.get("best_counts"):
        qual.append(f"Go-to counts: {', '.join(p['best_counts'])}")
    if p.get("confidence"):
        qual.append(f"Confidence: {p['confidence']}")
    if qual:
        lines.append(f"\nIn {name}'s words —\n" + "\n".join(qual))
    return Document(id=f"pitch:{pitch}", kind="pitch", title=f"{name} — {pitch}",
                    text="\n".join(lines), metadata={**meta, "pitch": pitch})


def _outing_doc(o: dict, name: str, meta: dict) -> Document:
    lines = [f"{name} outing report, {o.get('date_range') or 'undated'} ({o.get('filename', '')}). "
             f"Race to 2 strikes {o.get('race_to_2k') or 'n/a'}; "
             f"first-pitch strikes {o.get('first_pitch_strikes') or 'n/a'}."]
    for p in o.get("pitches", []):
        lines.append(
            f"- {p['name']}: {p.get('usage_count')} pitches ({p.get('usage_pct')}%), "
            f"{p.get('velo_low')}-{p.get('velo_high')} mph, "
            f"whiffs {p.get('whiffs', 'n/a')}/{p.get('swings', 'n/a')}, "
            f"strikes {p.get('strikes', 'n/a')}/{p.get('usage_count')}, "
            f"first-pitch strikes {p.get('fpk', 'n/a')}/{p.get('first_pitches', 'n/a')}.")
    return Document(id=f"outing:{o['id']}", kind="outing",
                    title=f"{name} — outing {o.get('date_range') or o.get('filename')}",
                    text="\n".join(lines),
                    metadata={**meta, "date_range": o.get("date_range"), "source": o.get("filename")})


# --- Hitter documents ---------------------------------------------------------------

def hitter_document(profile: dict, plan: dict, season: int) -> Document:
    """One MLB hitter's Statcast tendencies vs a pitcher hand, plus the rule-based plan."""
    hand = f"{profile['pitcher_hand']}HP"
    name = profile["name"]
    lines = [f"{name} ({profile.get('position', '')}, {profile.get('team', '')}), bats {profile['bats']}. "
             f"{season} vs {hand}: {plan['summary']}"]
    a = profile["approach"]
    lines.append(f"Approach vs {hand}: first-pitch swing {_num(a['first_pitch_swing_pct'], '%')}, "
                 f"chase before two strikes {_num(a['early_chase_pct'], '%')}, "
                 f"two-strike chase {_num(a['two_strike_chase_pct'], '%')}, "
                 f"two-strike whiff {_num(a['two_strike_whiff_pct'], '%')}.")
    for pitch, s in profile["by_pitch"].items():
        if s["pitches"] >= 25:
            lines.append(f"- vs {pitch} from {hand} ({s['pitches']} pitches): whiff {_num(s['whiff_pct'], '%')}, "
                         f"chase {_num(s['chase_pct'], '%')}, xwOBA on contact {_num(s['xwoba_con'], '', 3)}, "
                         f"run value {_num(s['rv100'], '', 1)} per 100 pitches.")
    z = plan.get("zones", {})
    if z.get("hot"):
        lines.append(f"Does the most damage {z['hot']['where']}; weakest contact "
                     f"{z.get('cold', {}).get('where', 'n/a')}.")
    if plan["recommendations"].get("Standard"):
        lines.append(f"\nRule-based plan vs this pitcher's arsenal: {plan['recommendations']['Standard']}")
    return Document(
        id=f"hitter:{profile['batter_id']}:{season}:{profile['pitcher_hand']}", kind="hitter",
        title=f"{name} — {season} vs {hand}", text="\n".join(lines),
        metadata={"hitter": name, "batter_id": profile["batter_id"], "team": profile.get("team", ""),
                  "season": season, "pitcher_hand": profile["pitcher_hand"]},
    )
