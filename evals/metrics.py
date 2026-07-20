"""Deterministic eval metrics for the monitoring-guidance RAG."""

from __future__ import annotations

from monitoring_guide.models import RagResult


def answered(result: RagResult) -> bool:
    return not result.answer.abstained


def citations_are_grounded(result: RagResult) -> bool:
    """Every citation quote must actually appear in the retrieved chunk it points at.
    (Catches fabricated/misattributed evidence.)"""
    by_id = {r.chunk.id: r.chunk.text for r in result.retrieved}
    for c in result.answer.citations:
        chunk_text = by_id.get(c.chunk_id)
        if chunk_text is None or c.quote.strip() not in chunk_text:
            return False
    return True


def retrieved_expected(result: RagResult, expected_doc: str) -> bool:
    """The expected source document appears among the retrieved chunks."""
    return any(r.chunk.doc_id == expected_doc for r in result.retrieved)
