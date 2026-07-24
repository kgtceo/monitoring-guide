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
from datetime import datetime, timezone
from pathlib import Path

from monitoring_guide.client import LLMClient
from monitoring_guide.config import Settings
from monitoring_guide.corpus import load_corpus
from monitoring_guide.embedder import VoyageEmbedder
from monitoring_guide.ingest import build_store
from monitoring_guide.rag import Rag

from metrics import answered, citations_are_grounded, retrieved_expected  # noqa: E402

DATASET = Path(__file__).parent / "dataset" / "questions.json"
RESULTS = Path(__file__).parent / "results" / "latest.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()

    settings = Settings.from_env()
    embedder = VoyageEmbedder(model=settings.embed_model)
    store = build_store(load_corpus(), embedder)
    client = LLMClient(settings)
    rag = Rag(embedder, store, client, min_retrieval_score=settings.min_retrieval_score)
    cases = json.loads(DATASET.read_text())

    failures: list[str] = []
    grades = []
    per_case: list[dict] = []
    for case in cases:
        result = rag.answer(case["question"])
        did_answer = answered(result)
        grounded = citations_are_grounded(result)
        top_score = result.retrieved[0].score if result.retrieved else None
        floor_refused = (
            top_score is not None and top_score < settings.min_retrieval_score
        )
        print(f"\n=== {case.get('trap') or case['question'][:60]} ===")
        print(f"  answered={did_answer} grounded={grounded} top_score={top_score and round(top_score,3)} "
              f"floor_refused={floor_refused} dropped_citations={len(result.dropped_citations)}")

        record: dict = {
            "question": case["question"][:80],
            "trap": case.get("trap"),
            "answered": did_answer,
            "grounded": grounded,
            "top_score": round(top_score, 3) if top_score is not None else None,
            "refused_by_floor": floor_refused,
            "dropped_citations": len(result.dropped_citations),
        }

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
            record["judge"] = g.model_dump()
            print(f"  JUDGE: faithful={g.faithful} abstention_ok={g.appropriate_abstention} overall={g.overall}")
            if not g.faithful:
                failures.append(f"{case['question'][:40]}: judge says unfaithful")

        per_case.append(record)

    if grades:
        n = len(grades)
        print(f"\n=== Judge averages === overall={sum(g.overall for g in grades)/n:.2f} "
              f"faithful={sum(g.faithful for g in grades)/n:.2f}")

    artifact = {
        "run": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": settings.answer_model,
            "embed_model": settings.embed_model,
            "judge_model": None if args.no_judge else settings.judge_model,
            "min_retrieval_score": settings.min_retrieval_score,
            "dataset_size": len(cases),
        },
        "metrics": {
            "judge_overall_avg": round(sum(g.overall for g in grades) / len(grades), 2) if grades else None,
            "all_grounded": all(c["grounded"] for c in per_case),
            "all_gates_passed": not failures,
        },
        "failures": failures,
        "per_case": per_case,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"\nWrote {RESULTS.relative_to(Path(__file__).parent.parent)}")

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
