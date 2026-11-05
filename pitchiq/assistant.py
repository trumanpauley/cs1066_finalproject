"""Scouting chatbot (RAG): retrieve the data a question needs, then stream Claude's answer.

Prompt layout (stable -> volatile, so the prompt cache keeps working):
    system   = instructions + the pitcher's knowledge documents   (cached)
    messages = earlier turns (append-only) + this turn's retrieved hitter
               data and notes + the question and report depth
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import anthropic

from pitchiq.config import CHAT_EFFORT, CHAT_MAX_TOKENS, CHAT_MODEL, CHAT_PRICES
from pitchiq.knowledge.documents import Chunk, Document, build_chunks
from pitchiq.knowledge.retrieval import BM25Index, find_hitters, find_teams

NOTES_INLINE_CHARS = 6000   # notes this short are sent whole; longer ones are searched
NOTE_CHUNKS = 4
MAX_HITTERS = 30            # a full active roster is ~13 position players

SYSTEM_PROMPT = """\
You are PitchIQ, a scouting assistant for a professional pitcher. You turn data into game plans he can remember on the mound.

Where your information comes from:
- <pitcher_profile> below: his arsenal from his own uploaded outing reports, plus what he wrote about how he throws and uses each pitch. Report samples are small (a few outings), so treat his rates as tendencies, not certainties.
- <scouting_data> in his messages: MLB hitters' 2026 Baseball Savant tendencies against his throwing hand, each with a rule-based plan computed from those numbers, and excerpts from his uploaded notes.

How to answer:
- Ground every claim about a hitter or about him in the data provided, and quote the key numbers (whiff %, chase %, xwOBA on contact, run value) so he can check them. Never invent statistics. If the data doesn't cover something he asks, say so plainly; general pitching strategy is fine when you label it as general.
- Build plans only from pitches in his arsenal. Give real weight to what he wrote about each pitch (how he throws it, plans vs righties/lefties, go-to counts, confidence). When his notes and the numbers disagree, say both and recommend one.
- The rule-based plan is a starting point computed mechanically; improve on it using his own notes and the matchup as a whole, and correct it if it contradicts the numbers.
- Describe locations from the hitter's point of view ("up and in", "down and away"), as the data does.
- He reads this in the dugout: plain language, short lines, one markdown heading per hitter, most dangerous hitters first. Follow the report-depth instruction in each message.
- If no team or hitter was found for a question that needs one, ask which team or hitter he means (a team name or a hitter's full name works best)."""

DEPTH_INSTRUCTIONS = {
    "Quick": "Report depth: QUICK. One or two short lines per hitter - the single thing to remember. "
             "Open with one line on the overall approach. No tables.",
    "Standard": "Report depth: STANDARD. Open with a 2-3 sentence overall approach for this lineup, then for "
                "each hitter 2-4 sentences: how to start him, the put-away pitch, what to avoid, and location.",
    "Detailed": "Report depth: DETAILED. Open with an overall approach, then for each hitter a count-by-count "
                "plan (0-0, ahead, behind, two strikes) with the supporting numbers and any sample-size "
                "caveats. End with 3-5 keys to the series.",
}


@dataclass
class RetrievedContext:
    teams: list[dict] = field(default_factory=list)
    hitters: list[dict] = field(default_factory=list)
    hitter_docs: list[Document] = field(default_factory=list)
    note_chunks: list[Chunk] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.hitter_docs and not self.note_chunks

    def source_titles(self) -> list[str]:
        return [d.title for d in self.hitter_docs] + [f"{c.title} (excerpt {c.id.rsplit('#', 1)[-1]})"
                                                      for c in self.note_chunks]


def retrieve(
    question: str,
    *,
    teams: list[dict],
    hitters: list[dict],
    roster_for: Callable[[dict], list[dict]],
    hitter_doc_for: Callable[[dict], Document],
    note_docs: list[Document],
    already_sent: set[str] = frozenset(),
    recent_hitter_ids: set[int] = frozenset(),
) -> RetrievedContext:
    """Everything this question needs that isn't already in the conversation.

    `roster_for(team)` and `hitter_doc_for(hitter)` are supplied by the caller
    (they hit the network / session cache), which keeps this function testable.
    Documents whose id is in `already_sent` are skipped - they are already in
    the conversation history, so follow-up questions don't resend them.
    `recent_hitter_ids` (hitters already discussed) settle ambiguous last
    names: "Freeman" after a Dodgers report means Freddie, not Tyler.
    """
    ctx = RetrievedContext(teams=find_teams(question, teams))
    wanted: dict[int, dict] = {}
    for team in ctx.teams:
        try:
            for h in roster_for(team):
                wanted.setdefault(h["id"], h)
        except Exception as exc:  # one failed roster shouldn't sink the answer
            ctx.failed.append(f"{team['name']} roster ({exc})")
    for h in find_hitters(question, hitters, prefer_ids=recent_hitter_ids):
        wanted.setdefault(h["id"], h)
    ctx.hitters = list(wanted.values())[:MAX_HITTERS]

    for h in ctx.hitters:
        try:
            doc = hitter_doc_for(h)
        except Exception as exc:
            ctx.failed.append(f"{h['name']} ({exc})")
            continue
        if doc.id not in already_sent:
            ctx.hitter_docs.append(doc)

    if note_docs:
        if sum(len(d.text) for d in note_docs) <= NOTES_INLINE_CHARS:
            chunks = build_chunks(note_docs)
        else:
            chunks = [c for c, _ in BM25Index(build_chunks(note_docs)).search(question, k=NOTE_CHUNKS)]
        ctx.note_chunks = [c for c in chunks if c.id not in already_sent]
    return ctx


def system_text(pitcher_docs: list[Document]) -> str:
    """Instructions + the pitcher's profile documents (same for every provider)."""
    profile = "\n\n".join(f'<document title="{d.title}">\n{d.text}\n</document>' for d in pitcher_docs)
    return f"{SYSTEM_PROMPT}\n\n<pitcher_profile>\n{profile}\n</pitcher_profile>"


def system_blocks_from_text(text: str) -> list[dict]:
    """Claude system prompt, cached across turns (it changes only when the profile does)."""
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def system_blocks(pitcher_docs: list[Document]) -> list[dict]:
    return system_blocks_from_text(system_text(pitcher_docs))


def user_turn(question: str, ctx: RetrievedContext, depth: str) -> str:
    parts = []
    if not ctx.empty:
        docs = [f'<document title="{d.title}">\n{d.text}\n</document>' for d in ctx.hitter_docs]
        docs += [f'<document title="{c.title}">\n{c.text}\n</document>' for c in ctx.note_chunks]
        parts.append("<scouting_data>\n" + "\n\n".join(docs) + "\n</scouting_data>")
    if ctx.failed:
        parts.append("Could not load: " + "; ".join(ctx.failed) + ".")
    parts.append(DEPTH_INSTRUCTIONS.get(depth, DEPTH_INSTRUCTIONS["Standard"]))
    parts.append(question)
    return "\n\n".join(parts)


class AnswerStream:
    """Iterate for text as it arrives; afterwards `.message` holds the full response.

    Opus 5.5 always thinks before answering (its thinking text isn't shown), so
    the first text can take a few seconds. A request a safety classifier
    declines is retried server-side on Anthropic's recommended fallback model.
    """

    def __init__(self, client: anthropic.Anthropic, system: list[dict], messages: list[dict]):
        self.client, self.system, self.messages = client, system, messages
        self.message = None

    def __iter__(self) -> Iterator[str]:
        with self.client.beta.messages.stream(
            model=CHAT_MODEL,
            max_tokens=CHAT_MAX_TOKENS,
            system=self.system,
            messages=self.messages,
            output_config={"effort": CHAT_EFFORT},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            yield from stream.text_stream
            self.message = stream.get_final_message()


def estimate_cost(usage) -> float:
    """Dollar cost of one response from its usage block (Claude API list prices)."""
    p = CHAT_PRICES
    return (
        (usage.input_tokens or 0) * p["input"]
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * p["cache_write"]
        + (getattr(usage, "cache_read_input_tokens", 0) or 0) * p["cache_read"]
        + (usage.output_tokens or 0) * p["output"]
    ) / 1_000_000
