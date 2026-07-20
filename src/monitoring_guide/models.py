"""Typed data contracts for the RAG pipeline.

The answer schema (`Answer`) is the tool schema handed to Claude, so the model
must reply as validated data — including per-claim citations and an explicit
`abstained` flag when the retrieved context doesn't support an answer. Grounding
is the whole point: a RAG system that answers beyond its sources is worse than one
that says "not in the documents".
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A retrievable unit of a source document."""

    id: str = Field(description="Stable id, e.g. '<doc>#<index>'.")
    doc_id: str
    index: int = Field(description="0-based position of the chunk within its document.")
    text: str


class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float = Field(description="Cosine similarity to the query (higher = closer).")


class Citation(BaseModel):
    chunk_id: str = Field(description="Which retrieved chunk supports the claim.")
    quote: str = Field(description="A short verbatim span from that chunk as evidence.")


class Answer(BaseModel):
    """The grounded answer. If the context is insufficient, abstain — do not guess."""

    answer: str = Field(
        description="The answer, using ONLY the retrieved context. If the context "
        "does not contain the answer, set abstained=true and say so plainly."
    )
    abstained: bool = Field(
        description="True when the retrieved context does not support an answer."
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Evidence for the answer — empty iff abstained. Every citation's "
        "quote must appear in the cited chunk.",
    )


class RagResult(BaseModel):
    """Everything the pipeline returns for one query — answer plus the retrieval trace."""

    query: str
    answer: Answer
    retrieved: list[RetrievedChunk]
