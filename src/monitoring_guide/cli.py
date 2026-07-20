"""`monitoring-guide` CLI — grounded Q&A over illustrative monitoring guidance.

    monitoring-guide ask "What monitoring does a patient on lithium need?"
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from .client import LLMClient
from .config import Settings
from .corpus import DISCLAIMER, load_corpus
from .embedder import VoyageEmbedder
from .ingest import build_store
from .rag import Rag

app = typer.Typer(add_completion=False, help="Grounded Q&A over illustrative drug/condition monitoring guidance.")
console = Console()


@app.callback()
def _root() -> None:
    """Grounded, cited monitoring-guidance Q&A (demo corpus; not clinical advice)."""


@app.command()
def ask(question: str = typer.Argument(..., help="Your monitoring question.")) -> None:
    settings = Settings.from_env()
    embedder = VoyageEmbedder(model=settings.embed_model)
    store = build_store(load_corpus(), embedder)
    rag = Rag(embedder, store, LLMClient(settings))

    with console.status("Retrieving guidance…"):
        result = rag.answer(question)

    a = result.answer
    style = "yellow" if a.abstained else "green"
    console.print(Panel(a.answer, title="Abstained" if a.abstained else "Answer", border_style=style))
    if a.citations:
        console.print("\n[bold]Citations:[/]")
        for c in a.citations:
            console.print(f"  [cyan]{c.chunk_id}[/] — “{c.quote}”")
    console.print(f"\n[dim]{DISCLAIMER}[/]")


if __name__ == "__main__":
    app()
