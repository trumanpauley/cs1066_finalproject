"""Retrieval for the scouting chatbot: find what a question is about, then fetch it.

Two kinds of retrieval, both deterministic and testable without an API key:

1. Entity lookup — teams ("Dodgers", "LAD", "Los Angeles Dodgers") and hitters
   ("Mookie Betts", accent-insensitive) named in the question. Structured data
   is fetched by ID, which is more reliable than similarity search for names.
2. BM25 keyword search — over free-text chunks (uploaded notes), so only the
   parts relevant to the question are sent to the model.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from pitchiq.knowledge.documents import Chunk

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from", "how", "i", "in",
    "is", "it", "me", "my", "of", "on", "or", "should", "the", "to", "vs", "what", "when",
    "with", "you", "your", "he", "his", "him", "this", "that", "them", "they", "their",
}


def normalize(text: str) -> str:
    """Lowercase and strip accents: 'José Ramírez' -> 'jose ramirez'."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(normalize(text)) if w not in _STOPWORDS]


# --- Entity lookup ---------------------------------------------------------------

def _contains_phrase(haystack: str, phrase: str) -> bool:
    return bool(phrase) and re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", haystack) is not None


def find_teams(question: str, teams: list[dict]) -> list[dict]:
    """Teams named by full name, nickname, or uppercase abbreviation ("LAD")."""
    q = normalize(question)
    found = []
    for t in teams:
        names = [normalize(t["name"]), normalize(t.get("nickname", ""))]
        by_name = any(_contains_phrase(q, n) for n in names if n)
        # Abbreviations only in capitals, so "sd" or "tex" inside normal words don't match.
        abbr = t.get("abbreviation", "")
        by_abbr = len(abbr) >= 2 and re.search(rf"(?<![A-Za-z]){re.escape(abbr)}(?![A-Za-z])", question)
        if by_name or by_abbr:
            found.append(t)
    return found


def find_hitters(question: str, hitters: list[dict], prefer_ids: set[int] = frozenset()) -> list[dict]:
    """Hitters named in full, or by a last name that is unique in the league.

    A last name shared by several hitters ("Freeman") resolves to the one in
    `prefer_ids` (hitters already in the conversation) when exactly one matches.
    """
    q = normalize(question)
    found = {h["id"]: h for h in hitters if _contains_phrase(q, normalize(h["name"]))}

    # Last name alone: must be capitalized in the question ("Betts", not "bets"),
    # at least 4 letters, and belong to exactly one hitter in the league.
    capitalized = {normalize(w) for w in re.findall(r"[^\W\d_][\w'’-]*", question) if w[0].isupper()}
    by_last: dict[str, list[dict]] = {}
    for h in hitters:
        by_last.setdefault(_last_name(h), []).append(h)
    for last in capitalized:
        candidates = by_last.get(last, [])
        if len(last) < 4 or not candidates:
            continue
        if len(candidates) > 1:
            candidates = [h for h in candidates if h["id"] in prefer_ids]
        if len(candidates) == 1:
            found.setdefault(candidates[0]["id"], candidates[0])
    return list(found.values())


def _last_name(hitter: dict) -> str:
    """'Ronald Acuña Jr.' -> 'acuna' (suffixes skipped)."""
    parts = [p for p in normalize(hitter["name"]).split() if p.rstrip(".") not in {"jr", "sr", "ii", "iii", "iv"}]
    return parts[-1] if parts else ""


# --- BM25 over chunks --------------------------------------------------------------

class BM25Index:
    """Okapi BM25 (k1=1.5, b=0.75) over chunk text."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(c.text)) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = (sum(self.lengths) / len(self.lengths)) if chunks else 0.0
        df = Counter(term for d in self.docs for term in d)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 4) -> list[tuple[Chunk, float]]:
        terms = tokenize(query)
        scored = []
        for chunk, doc, length in zip(self.chunks, self.docs, self.lengths):
            score = 0.0
            for t in terms:
                tf = doc.get(t, 0)
                if tf:
                    norm = tf + self.k1 * (1 - self.b + self.b * length / (self.avg_len or 1))
                    score += self.idf[t] * tf * (self.k1 + 1) / norm
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda cs: -cs[1])
        return scored[:k]
