"""Ingestion: documents -> chunks -> embeddings -> a searchable VectorStore."""

from __future__ import annotations

from pathlib import Path

from .chunking import chunk_document
from .embedder import Embedder
from .models import Chunk
from .store import VectorStore


def build_store(
    documents: dict[str, str],
    embedder: Embedder,
    *,
    chunk_size: int = 200,
    overlap: int = 40,
) -> VectorStore:
    """Chunk every document, embed all chunks in one batch, and index them.

    `documents` maps a doc_id (e.g. a filename) to its raw text.
    """
    chunks: list[Chunk] = []
    for doc_id, text in documents.items():
        chunks.extend(
            chunk_document(doc_id, text, chunk_size=chunk_size, overlap=overlap)
        )

    store = VectorStore()
    if chunks:
        embeddings = embedder.embed([c.text for c in chunks], is_query=False)
        store.add(chunks, embeddings)
    return store


def load_documents(paths: list[Path]) -> dict[str, str]:
    """Read text/markdown files into a {doc_id: text} map keyed by file name."""
    return {p.name: p.read_text(encoding="utf-8") for p in paths}
