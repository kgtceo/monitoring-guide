"""The RAG pipeline: question -> retrieve monitoring guidance -> grounded, cited answer.

Pure orchestration over embedder + store + LLM client, so it's unit-testable with fakes.
"""

from __future__ import annotations

from . import prompts
from .client import LLMClient
from .embedder import Embedder
from .models import Answer, RagResult, RetrievedChunk
from .store import VectorStore


class Rag:
    def __init__(self, embedder: Embedder, store: VectorStore, client: LLMClient) -> None:
        self._embedder = embedder
        self._store = store
        self._client = client

    def retrieve(self, query: str, k: int = 4) -> list[RetrievedChunk]:
        query_vec = self._embedder.embed([query], is_query=True)[0]
        return self._store.search(query_vec, k)

    def answer(self, query: str, k: int = 4) -> RagResult:
        retrieved = self.retrieve(query, k)
        if not retrieved:
            return RagResult(
                query=query,
                answer=Answer(answer="No guidance is indexed, so I can't answer that.", abstained=True, citations=[]),
                retrieved=[],
            )
        passages = [(r.chunk.id, r.chunk.text) for r in retrieved]
        answer = self._client.structured(
            schema=Answer,
            system=prompts.ANSWER_SYSTEM,
            user=prompts.answer_user(query, passages),
        )
        return RagResult(query=query, answer=answer, retrieved=retrieved)
