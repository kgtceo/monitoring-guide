"""Chunking — the most under-appreciated RAG knob.

Chunk size and overlap materially change retrieval quality — the values here (200-word
windows, 40 overlap) were picked by hand for this small corpus, not swept; a real system
would benchmark configurations. This splitter is word-based with overlap:
simple, deterministic, and paragraph-aware (it prefers to break on blank lines so a
chunk doesn't split mid-thought when possible).
"""

from __future__ import annotations

import re

from .models import Chunk

_PARA = re.compile(r"\n\s*\n")


def _words(text: str) -> list[str]:
    return text.split()


def chunk_document(
    doc_id: str, text: str, *, chunk_size: int = 200, overlap: int = 40
) -> list[Chunk]:
    """Split `text` into ~`chunk_size`-word chunks with `overlap`-word overlap.

    Paragraphs shorter than the chunk size are kept whole; longer ones are windowed.
    Overlap carries context across boundaries so an answer that straddles two chunks
    is still retrievable.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[Chunk] = []
    index = 0
    for para in _PARA.split(text):
        words = _words(para)
        if not words:
            continue
        start = 0
        while start < len(words):
            window = words[start : start + chunk_size]
            chunks.append(
                Chunk(
                    id=f"{doc_id}#{index}",
                    doc_id=doc_id,
                    index=index,
                    text=" ".join(window),
                )
            )
            index += 1
            if start + chunk_size >= len(words):
                break
            start += chunk_size - overlap
    return chunks
