"""monitoring-guide — grounded Q&A over an illustrative corpus of UK primary-care drug/condition
monitoring guidance. Cites its sources and abstains when the corpus doesn't cover the question.

DEMO / EDUCATIONAL — not clinical advice, not a substitute for current guidance."""

from .client import LLMClient
from .config import Settings
from .corpus import DISCLAIMER, load_corpus
from .embedder import Embedder, FakeEmbedder, VoyageEmbedder
from .ingest import build_store
from .models import Answer, Citation, RagResult, RetrievedChunk
from .rag import Rag
from .store import VectorStore

__all__ = [
    "LLMClient",
    "Settings",
    "DISCLAIMER",
    "load_corpus",
    "Embedder",
    "FakeEmbedder",
    "VoyageEmbedder",
    "build_store",
    "Answer",
    "Citation",
    "RagResult",
    "RetrievedChunk",
    "Rag",
    "VectorStore",
]
