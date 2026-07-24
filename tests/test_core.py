"""Offline tests: chunking, retrieval plumbing, grounded-answer path, and corpus loading."""

from __future__ import annotations

from conftest import FakeAnswerClient

from monitoring_guide.chunking import chunk_document
from monitoring_guide.corpus import load_corpus
from monitoring_guide.embedder import FakeEmbedder
from monitoring_guide.ingest import build_store
from monitoring_guide.models import Answer, Citation
from monitoring_guide.rag import Rag


def test_corpus_loads_bundled_guidance():
    corpus = load_corpus()
    assert "high_risk_drugs.md" in corpus
    assert "long_term_conditions.md" in corpus
    assert "lithium" in corpus["high_risk_drugs.md"].lower()


def test_chunking_overlap():
    text = "para one here. " * 100
    chunks = chunk_document("d", text, chunk_size=50, overlap=10)
    assert len(chunks) >= 2
    assert all(c.doc_id == "d" for c in chunks)


def test_build_store_and_retrieve_offline():
    store = build_store(load_corpus(), FakeEmbedder())
    assert len(store) > 0
    embedder = FakeEmbedder()
    qv = embedder.embed(["lithium monitoring"], is_query=True)[0]
    hits = store.search(qv, k=3)
    assert len(hits) == 3  # retrieval plumbing works (FakeEmbedder isn't semantic)


def test_answer_path_returns_grounded_result():
    corpus = {"doc.md": "Lithium needs a level every 3 months."}
    store = build_store(corpus, FakeEmbedder())
    chunk_id = store.search(FakeEmbedder().embed(["lithium"], is_query=True)[0], k=1)[0].chunk.id
    client = FakeAnswerClient(Answer(
        answer="Every 3 months.", abstained=False,
        citations=[Citation(chunk_id=chunk_id, quote="every 3 months")],
    ))
    rag = Rag(FakeEmbedder(), store, client)
    result = rag.answer("How often is lithium checked?")
    assert result.answer.abstained is False
    assert result.answer.citations[0].chunk_id == chunk_id


def test_empty_store_abstains_without_calling_llm():
    from monitoring_guide.store import VectorStore

    client = FakeAnswerClient()
    rag = Rag(FakeEmbedder(), VectorStore(), client)
    result = rag.answer("anything")
    assert result.answer.abstained is True
    assert client.calls == 0


def test_retrieval_floor_abstains_without_calling_llm():
    """Below the abstention floor, out-of-scope questions never reach the LLM."""
    corpus = {"doc.md": "Lithium needs a level every 3 months."}
    store = build_store(corpus, FakeEmbedder())
    client = FakeAnswerClient()
    rag = Rag(FakeEmbedder(), store, client, min_retrieval_score=0.99)  # floor above any score
    result = rag.answer("Who won the football world cup?")
    assert result.answer.abstained is True
    assert "outside the indexed" in result.answer.answer
    assert client.calls == 0


def test_fabricated_citation_is_dropped_and_answer_withheld():
    """RUNTIME grounding: a citation whose quote is not verbatim in the cited chunk is
    dropped; an answered response with no surviving citation is forced to abstain."""
    corpus = {"doc.md": "Lithium needs a level every 3 months."}
    store = build_store(corpus, FakeEmbedder())
    chunk_id = store.search(FakeEmbedder().embed(["lithium"], is_query=True)[0], k=1)[0].chunk.id
    client = FakeAnswerClient(Answer(
        answer="Lithium levels are checked weekly.", abstained=False,
        citations=[Citation(chunk_id=chunk_id, quote="checked weekly without fail")],  # fabricated
    ))
    rag = Rag(FakeEmbedder(), store, client)
    result = rag.answer("How often is lithium checked?")
    assert result.answer.abstained is True
    assert result.answer.citations == []
    assert len(result.dropped_citations) == 1


def test_partial_citations_keep_answer_but_drop_bad_ones():
    corpus = {"doc.md": "Lithium needs a level every 3 months."}
    store = build_store(corpus, FakeEmbedder())
    chunk_id = store.search(FakeEmbedder().embed(["lithium"], is_query=True)[0], k=1)[0].chunk.id
    client = FakeAnswerClient(Answer(
        answer="Every 3 months.", abstained=False,
        citations=[
            Citation(chunk_id=chunk_id, quote="every 3 months"),          # grounded
            Citation(chunk_id=chunk_id, quote="and annually thereafter"),  # fabricated
            Citation(chunk_id="nonexistent#0", quote="every 3 months"),    # wrong chunk
        ],
    ))
    rag = Rag(FakeEmbedder(), store, client)
    result = rag.answer("How often is lithium checked?")
    assert result.answer.abstained is False
    assert len(result.answer.citations) == 1
    assert len(result.dropped_citations) == 2


def test_citation_grounding_is_case_and_whitespace_insensitive():
    corpus = {"doc.md": "Lithium needs a LEVEL   every 3 months."}
    store = build_store(corpus, FakeEmbedder())
    chunk_id = store.search(FakeEmbedder().embed(["lithium"], is_query=True)[0], k=1)[0].chunk.id
    client = FakeAnswerClient(Answer(
        answer="Every 3 months.", abstained=False,
        citations=[Citation(chunk_id=chunk_id, quote="level every 3 months")],
    ))
    rag = Rag(FakeEmbedder(), store, client)
    result = rag.answer("How often is lithium checked?")
    assert result.answer.abstained is False and len(result.answer.citations) == 1


def test_abstention_normalises_stray_citations_away():
    corpus = {"doc.md": "Lithium needs a level every 3 months."}
    store = build_store(corpus, FakeEmbedder())
    chunk_id = store.search(FakeEmbedder().embed(["lithium"], is_query=True)[0], k=1)[0].chunk.id
    client = FakeAnswerClient(Answer(
        answer="Not in the sources.", abstained=True,
        citations=[Citation(chunk_id=chunk_id, quote="every 3 months")],  # stray
    ))
    rag = Rag(FakeEmbedder(), store, client)
    result = rag.answer("How often is lithium checked?")
    assert result.answer.abstained is True and result.answer.citations == []
