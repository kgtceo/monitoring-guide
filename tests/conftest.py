"""Offline test doubles — FakeEmbedder + a fake answer client, no API keys, no network."""

from __future__ import annotations

import pytest

from monitoring_guide.config import Settings
from monitoring_guide.models import Answer, Citation


class FakeAnswerClient:
    """Returns a scripted Answer. Default cites the top retrieved chunk with a real quote if given."""

    def __init__(self, answer: Answer | None = None) -> None:
        self._answer = answer
        self.calls = 0

    def structured(self, *, schema, system, user, model=None):
        self.calls += 1
        if self._answer is not None:
            return self._answer
        return Answer(answer="See guidance.", abstained=False, citations=[])


@pytest.fixture
def settings() -> Settings:
    return Settings(anthropic_api_key="test-key")


@pytest.fixture
def answer_cite():
    def _make(chunk_id: str, quote: str) -> Answer:
        return Answer(answer="Answer grounded in guidance.", abstained=False,
                      citations=[Citation(chunk_id=chunk_id, quote=quote)])
    return _make
