"""Load the bundled illustrative monitoring-guidance corpus (the *.md files in data/guidance)."""

from __future__ import annotations

from pathlib import Path

_GUIDANCE_DIR = Path(__file__).parent / "data" / "guidance"

DISCLAIMER = (
    "Demo/educational tool. Answers come only from a small illustrative corpus paraphrased from "
    "public UK guidance — not clinical advice, and not a substitute for current guidance."
)


def load_corpus() -> dict[str, str]:
    """{doc_id: text} for every markdown file in the bundled guidance directory."""
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_GUIDANCE_DIR.glob("*.md"))}
