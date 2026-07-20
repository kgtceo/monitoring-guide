"""Run the monitoring-guide eval suite (needs ANTHROPIC + VOYAGE keys).

Gates:
  • RETRIEVAL   — the expected source doc is retrieved for in-corpus questions.
  • ABSTENTION  — out-of-corpus questions are refused, not answered.
  • GROUNDING   — every citation quote appears in its cited chunk (deterministic).
  • JUDGE       — opus confirms faithfulness + appropriate abstention.

    python evals/run_evals.py [--no-judge]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from monitoring_guide.client import LLMClient
from monitoring_guide.config import Settings
from monitoring_guide.corpus import load_corpus
from monitoring_guide.embedder import VoyageEmbedder
from monitoring_guide.ingest import build_store
from monitoring_guide.rag import Rag

from metrics import answered, citations_are_grounded, retrieved_expected  # noqa: E402

DATASET = Path(__file__).parent / "dataset" / "questions.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()

    settings = Settings.from_env()
    embedder = VoyageEmbedder(model=settings.embed_model)
    store = build_store(load_corpus(), embedder)
    client = LLMClient(settings)
    rag = Rag(embedder, store, client)
    cases = json.loads(DATASET.read_text())

    failures: list[str] = []
    grades = []
    for case in cases:
        result = rag.answer(case["question"])
        did_answer = answered(result)
        grounded = citations_are_grounded(result)
        print(f"\n=== {case['question'][:60]} ===")
        print(f"  answered={did_answer} grounded={grounded} retrieved={[r.chunk.doc_id for r in result.retrieved]}")

        if case["expect_answer"]:
            if not did_answer:
                failures.append(f"{case['question'][:40]}: expected an answer, abstained")
            if case.get("expected_doc") and not retrieved_expected(result, case["expected_doc"]):
                failures.append(f"{case['question'][:40]}: expected doc {case['expected_doc']} not retrieved")
        else:
            if did_answer:
                failures.append(f"{case['question'][:40]}: expected abstention, answered anyway")
        if not grounded:
            failures.append(f"{case['question'][:40]}: a citation quote isn't in its chunk")

        if not args.no_judge:
            from judge import grade  # noqa: E402

            g = grade(result, settings, client)
            grades.append(g)
            print(f"  JUDGE: faithful={g.faithful} abstention_ok={g.appropriate_abstention} overall={g.overall}")
            if not g.faithful:
                failures.append(f"{case['question'][:40]}: judge says unfaithful")

    if grades:
        n = len(grades)
        print(f"\n=== Judge averages === overall={sum(g.overall for g in grades)/n:.2f} "
              f"faithful={sum(g.faithful for g in grades)/n:.2f}")

    print("\n" + "=" * 40)
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("ALL GATES PASSED ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
