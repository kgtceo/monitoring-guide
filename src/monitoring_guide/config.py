"""Runtime configuration (MG_ prefix). Anthropic for answering, Voyage for embeddings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
        return
    except ImportError:
        pass
    cwd = Path.cwd()
    for directory in (cwd, *cwd.parents):
        env_file = directory / ".env"
        if env_file.is_file():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
            return


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    answer_model: str = os.getenv("MG_ANSWER_MODEL", "claude-sonnet-4-6")
    judge_model: str = os.getenv("MG_JUDGE_MODEL", "claude-opus-4-8")
    embed_model: str = os.getenv("MG_EMBED_MODEL", "voyage-3")
    max_tokens: int = int(os.getenv("MG_MAX_TOKENS", "1500"))
    # Deterministic abstention floor: if the best retrieval cosine is below this, the
    # question is out of scope and we abstain WITHOUT calling the LLM. Chosen from measured
    # distributions (voyage-3): in-corpus questions top 0.64-0.77, out-of-corpus 0.20-0.38.
    min_retrieval_score: float = float(os.getenv("MG_MIN_RETRIEVAL_SCORE", "0.45"))
    max_schema_retries: int = int(os.getenv("MG_MAX_SCHEMA_RETRIES", "2"))

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your keys.")
        return cls(anthropic_api_key=key)
