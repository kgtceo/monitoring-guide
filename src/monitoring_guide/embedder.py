"""Embedding providers behind a small interface.

Anthropic has no embeddings API, so retrieval uses Voyage AI (Anthropic's
recommended partner — lightweight, deploys anywhere, free tier). It sits behind an
`Embedder` protocol so it's swappable (a local sentence-transformers model, OpenAI,
etc.) without touching the pipeline — and so tests use a deterministic FakeEmbedder
with no network.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        """Return an (len(texts), dim) float32 array of L2-normalised embeddings."""
        ...


def _l2_normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype("float32")


class VoyageEmbedder:
    """Voyage AI embeddings. Uses distinct input types for documents vs queries,
    which measurably improves retrieval over embedding both the same way."""

    def __init__(self, model: str = "voyage-3", api_key: str | None = None) -> None:
        import os

        import voyageai

        self.model = model
        self._client = voyageai.Client(api_key=api_key or os.getenv("VOYAGE_API_KEY"))
        # voyage-3 is 1024-dim; keep it explicit so the store can pre-size.
        self.dim = 1024

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        result = self._client.embed(
            texts,
            model=self.model,
            input_type="query" if is_query else "document",
        )
        return _l2_normalize(np.array(result.embeddings, dtype="float32"))


class FakeEmbedder:
    """Deterministic, network-free embeddings for tests. Hashes text into a vector so
    identical text embeds identically and retrieval plumbing is exercisable offline.
    (Not semantic — real relevance needs a real model.)"""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        rows = []
        for t in texts:
            seed = int.from_bytes(hashlib.sha256(t.encode()).digest()[:8], "big")
            rng = np.random.default_rng(seed)
            rows.append(rng.standard_normal(self.dim))
        return _l2_normalize(np.array(rows, dtype="float32"))
