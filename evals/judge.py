"""LLM-as-judge (opus): is the answer faithful to the cited guidance and correctly abstaining?"""

from __future__ import annotations

from pydantic import BaseModel, Field

from monitoring_guide.client import LLMClient
from monitoring_guide.config import Settings
from monitoring_guide.models import RagResult


class FaithfulnessGrade(BaseModel):
    faithful: bool = Field(description="Is every claim supported by the retrieved passages (no outside knowledge)?")
    appropriate_abstention: bool = Field(description="If it abstained, was that right? If it answered, was answering right?")
    overall: int = Field(ge=1, le=5)
    comment: str = ""


JUDGE_SYSTEM = (
    "You grade a monitoring-guidance RAG answer. Given the QUESTION, the retrieved PASSAGES and the "
    "ANSWER, judge: (1) faithful — is every claim supported by the passages, with no outside medical "
    "knowledge added? (2) appropriate_abstention — was abstaining/answering the right call given the "
    "passages? Be strict; a wrong monitoring interval or unsupported claim = not faithful."
)


def grade(result: RagResult, settings: Settings, client: LLMClient | None = None) -> FaithfulnessGrade:
    client = client or LLMClient(settings)
    passages = "\n\n".join(f"[{r.chunk.id}] {r.chunk.text}" for r in result.retrieved) or "(none)"
    user = (
        f"QUESTION: {result.query}\n\nPASSAGES:\n{passages}\n\n"
        f"ANSWER (abstained={result.answer.abstained}): {result.answer.answer}"
    )
    return client.structured(schema=FaithfulnessGrade, system=JUDGE_SYSTEM, user=user, model=settings.judge_model)
