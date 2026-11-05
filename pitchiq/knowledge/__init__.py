"""Knowledge base for the future scouting chatbot (RAG).

Everything PitchIQ knows is turned into plain-text `Document`s with metadata,
then split into `Chunk`s. A retriever (embeddings + vector search) will index
the chunks; the chatbot then answers from the retrieved chunks.

    pitcher_documents(profile)        -> overview, one doc per pitch, per outing, per notes file
    hitter_document(profile, plan)    -> one doc per MLB hitter (Savant tendencies + plan)
    build_chunks(documents)           -> chunks ready to embed
"""

from pitchiq.knowledge.documents import (
    Chunk,
    Document,
    build_chunks,
    chunk_text,
    hitter_document,
    pitcher_documents,
)

__all__ = ["Chunk", "Document", "build_chunks", "chunk_text", "hitter_document", "pitcher_documents"]
