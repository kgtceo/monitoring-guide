"""A tiny in-memory vector store.

Retrieval is implemented transparently (normalised embeddings → cosine similarity
is a single matrix–vector dot product) rather than hidden behind a vector DB. For a
corpus of hundreds–thousands of chunks this is fast, dependency-free, and makes the
retrieval metrics in evals/ easy to reason about. Swap in FAISS/pgvector when the
corpus outgrows memory — the interface is the same.
"""

from __future__ import annotations

import numpy as np

from .models import Chunk, RetrievedChunk


class VectorStore:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._matrix: np.ndarray | None = None  # (n_chunks, dim), L2-normalised

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        if len(chunks) != embeddings.shape[0]:
            raise ValueError("chunks and embeddings length mismatch")
        self._chunks.extend(chunks)
        self._matrix = (
            embeddings
            if self._matrix is None
            else np.vstack([self._matrix, embeddings])
        )

    def search(self, query_embedding: np.ndarray, k: int) -> list[RetrievedChunk]:
        if self._matrix is None or not self._chunks:
            return []
        # Both sides are L2-normalised, so dot product == cosine similarity.
        scores = self._matrix @ query_embedding.reshape(-1)
        top = np.argsort(-scores)[: min(k, len(self._chunks))]
        return [
            RetrievedChunk(chunk=self._chunks[i], score=float(scores[i])) for i in top
        ]
