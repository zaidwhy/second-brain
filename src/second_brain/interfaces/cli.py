"""Second Brain++ CLI - vault, search, related, and graph commands.

Personal LLM is imported lazily inside each command so the module (and the test suite)
loads without the heavy embedding/vector dependencies. Run `pip install -e ../personal-llm`
before using the commands for real.
"""

from __future__ import annotations

from pathlib import Path

import typer

from second_brain.config import get_settings

app = typer.Typer(help="Second Brain++ - an AI knowledge layer over your Personal LLM core.")


def _engine():
    # Default the graph's extraction model to a capable local one, unless the user set their
    # own OLLAMA_MODEL. Personal LLM's router reads OLLAMA_MODEL, so set it before building.
    import os

    os.environ.setdefault("OLLAMA_MODEL", get_settings().ollama_model)
    from personal_llm.engine import build_engine

    return build_engine()


@app.command("ingest-vault")
def ingest_vault_cmd(
    vault: Path = typer.Argument(None, help="Vault folder (defaults to config vault_dir)."),
    force: bool = typer.Option(False, "--force", help="Re-ingest every file, ignoring the manifest."),
) -> None:
    """Ingest all changed notes under a vault folder into the Personal LLM core."""
    from personal_llm.memory.ingest import ingest_file

    from second_brain.vault import ingest_vault

    settings = get_settings()
    vault_dir = vault or settings.vault_dir
    engine = _engine()
    report = ingest_vault(
        vault_dir,
        settings.manifest_path,
        lambda path: ingest_file(engine.store, engine.vectors, engine.router, path),
        force=force,
    )
    typer.echo(f"Ingested {len(report.ingested)}, skipped {len(report.skipped)} (total {report.total}).")


@app.command()
def search(query: str, k: int = typer.Option(5, help="Number of results.")) -> None:
    """Semantic search across everything ingested."""
    from personal_llm.memory.retrieve import semantic_search

    engine = _engine()
    hits = semantic_search(engine.store, engine.vectors, engine.router, query, k=k)
    if not hits:
        typer.echo("No matches yet - ingest a vault first.")
        return
    for hit in hits:
        typer.echo(f"[{hit.rank_score:.3f}] {hit.source}: {' '.join(hit.text.split())[:120]}")


@app.command()
def related(note: Path, k: int = typer.Option(5, help="Number of related notes.")) -> None:
    """Show the notes most related to a given note (auto-linking)."""
    from personal_llm.memory.retrieve import semantic_search

    from second_brain.links import related_notes

    engine = _engine()
    note = Path(note)
    text = note.read_text(encoding="utf-8", errors="replace")
    source_doc_id = str(note.resolve())

    def search_fn(query: str, kk: int):
        return semantic_search(engine.store, engine.vectors, engine.router, query, k=kk)

    results = related_notes(search_fn, text=text, source_doc_id=source_doc_id, k=k)
    if not results:
        typer.echo("No related notes found.")
        return
    for result in results:
        typer.echo(f"[{result.score:.3f} x{result.hit_count}] {result.source}: {result.snippet[:100]}")


@app.command()
def graph(out: Path = typer.Option(None, help="Output HTML path (defaults to config graph_html_path).")) -> None:
    """Export the knowledge graph to a self-contained, offline HTML visualization."""
    from second_brain.graphview import render_html, to_nodelink

    settings = get_settings()
    engine = _engine()
    nodelink = to_nodelink(engine.store.all_nodes(), engine.store.all_edges())
    out = Path(out) if out else settings.graph_html_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(nodelink), encoding="utf-8")
    typer.echo(f"Wrote {len(nodelink.nodes)} nodes, {len(nodelink.links)} links to {out}")


@app.command("predict-links")
def predict_links_cmd(
    k: int = typer.Option(10, help="Number of predicted links to show."),
    min_score: int = typer.Option(1, help="Minimum shared-neighbor count to report."),
) -> None:
    """Suggest missing links: note pairs sharing neighbors but not yet connected."""
    from second_brain.link_predict import predict_links

    engine = _engine()
    predictions = predict_links(
        engine.store.all_nodes(), engine.store.all_edges(), k=k, min_score=min_score
    )
    if not predictions:
        typer.echo("No link predictions - graph is too sparse or fully connected.")
        return
    for p in predictions:
        shared = ", ".join(sorted(p.common_neighbors))
        typer.echo(f"[{p.score}] {p.node_a} <-> {p.node_b} (shared: {shared})")


@app.command("add-note")
def add_note_cmd(
    text: str = typer.Argument(..., help="The note text to remember (quote it)."),
    label: str = typer.Option("note", "--label", "-l", help="A short name shown in search results."),
) -> None:
    """Add a single note straight into Second Brain - no file needed."""
    from datetime import datetime, timezone

    from personal_llm.memory.ingest import ingest_text

    engine = _engine()
    doc_id = f"{label}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    result = ingest_text(engine.store, engine.vectors, engine.router, text=text, doc_id=doc_id, source=label)
    typer.echo(f"Added '{label}' ({result.chunks_ingested} chunk(s), {result.kg_triples} graph triple(s)).")


@app.command("code-graph")
def code_graph_cmd(
    target: str = typer.Argument(".", help="Directory or URL for Graphify to analyze."),
    out: Path = typer.Option(Path("data/code-graph.html"), help="Output HTML path."),
    full: bool = typer.Option(
        False, "--full", help="Run Graphify's full LLM clustering (needs a provider API key)."
    ),
    merge_notes: bool = typer.Option(
        False, "--merge-notes", help="Also merge in the notes knowledge graph from the core."
    ),
) -> None:
    """Build a code/repo knowledge graph with Graphify and render it in our offline viewer.

    Requires Graphify: `pip install graphifyy`. Graphify is optional - the rest of Second
    Brain works without it. By default this uses Graphify's no-LLM extraction.
    """
    from second_brain.graphify_adapter import (
        GraphifyNotInstalled,
        load_graphify_graph,
        merge,
        run_graphify,
    )
    from second_brain.graphview import render_html, to_nodelink

    try:
        json_path = run_graphify(target, no_cluster=not full)
    except GraphifyNotInstalled as exc:
        typer.echo(str(exc))
        raise typer.Exit(1)

    graph = load_graphify_graph(json_path)
    if merge_notes:
        engine = _engine()
        notes_graph = to_nodelink(engine.store.all_nodes(), engine.store.all_edges())
        graph = merge(graph, notes_graph)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(graph, title="Second Brain - Code Graph"), encoding="utf-8")
    typer.echo(f"Wrote {len(graph.nodes)} nodes, {len(graph.links)} links to {out}")


if __name__ == "__main__":
    app()
