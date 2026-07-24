"""The RAG pipeline: question -> retrieve monitoring guidance -> grounded, cited answer.

Grounding is ENFORCED AT RUNTIME, not just measured in evals:

  • Abstention floor — if the best retrieval cosine is below `min_retrieval_score`, the
    question is out of scope and we abstain deterministically, without calling the LLM.
    (Threshold chosen from measured distributions: in-corpus questions top ~0.64-0.77,
    out-of-corpus ~0.20-0.38 with voyage-3.)
  • Citation grounding — every citation's quote must be a verbatim substring
    (whitespace/case-normalised) of the chunk it cites, and the chunk must be one that was
    actually retrieved. Failing citations are DROPPED (surfaced on the result), and an
    answered response whose citations all fail is forced to abstain — an uncited answer is
    worse than no answer.

Pure orchestration over embedder + store + LLM client, so it's unit-testable with fakes.
"""

from __future__ import annotations

import re

from . import prompts
from .client import LLMClient
from .embedder import Embedder
from .models import Answer, Citation, RagResult, RetrievedChunk
from .store import VectorStore

_UNGROUNDED_ABSTAIN = (
    "The answer could not be grounded in the indexed guidance (its citations failed "
    "verification), so it has been withheld. Please rephrase or consult the source guidance."
)
_OUT_OF_SCOPE_ABSTAIN = (
    "That question is outside the indexed monitoring guidance, so I can't answer it from "
    "these sources."
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


class Rag:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        client: LLMClient,
        *,
        min_retrieval_score: float = -1.0,  # -1.0 = floor off (cosine ≥ -1); production
                                            # wiring passes Settings.min_retrieval_score (0.45)
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._client = client
        self._min_score = min_retrieval_score

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
        # Deterministic abstention floor — out-of-scope questions never reach the LLM.
        if retrieved[0].score < self._min_score:
            return RagResult(
                query=query,
                answer=Answer(answer=_OUT_OF_SCOPE_ABSTAIN, abstained=True, citations=[]),
                retrieved=retrieved,
            )

        passages = [(r.chunk.id, r.chunk.text) for r in retrieved]
        answer = self._client.structured(
            schema=Answer,
            system=prompts.ANSWER_SYSTEM,
            user=prompts.answer_user(query, passages),
        )
        answer, dropped = self._ground(answer, retrieved)
        return RagResult(query=query, answer=answer, retrieved=retrieved, dropped_citations=dropped)

    @staticmethod
    def _ground(answer: Answer, retrieved: list[RetrievedChunk]) -> tuple[Answer, list[Citation]]:
        """Runtime enforcement of the citation contract (see module docstring)."""
        chunk_texts = {r.chunk.id: _norm(r.chunk.text) for r in retrieved}
        kept: list[Citation] = []
        dropped: list[Citation] = []
        for c in answer.citations:
            text = chunk_texts.get(c.chunk_id)
            quote = _norm(c.quote)
            if text is not None and quote and quote in text:
                kept.append(c)
            else:
                dropped.append(c)

        if answer.abstained:
            # An abstention carries no citations — normalise any strays away.
            return answer.model_copy(update={"citations": []}), dropped + kept

        if not kept:
            # Answered but nothing verifiable survived → the answer is withheld.
            return Answer(answer=_UNGROUNDED_ABSTAIN, abstained=True, citations=[]), dropped
        return answer.model_copy(update={"citations": kept}), dropped
