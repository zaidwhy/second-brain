# Second Brain++

**Your Mind. Expanded.** An AI knowledge layer built on top of the [Personal LLM](../personal-llm) core.

Personal LLM already gives us memory, RAG, and a knowledge graph. Second Brain++ adds the
vault-level workflows the core does not:

- **Vault ingestion** - point it at a folder of notes and it ingests every changed file,
  skipping unchanged ones via a content-hash manifest (`ingest-vault`).
- **Auto-linking** - given a note, surface the most related *other* notes, aggregated at
  the document level rather than as raw chunks (`related`).
- **Knowledge-graph view** - export the graph to a single self-contained, offline HTML
  visualization with an inline force layout, no CDN (`graph`).
- **Semantic search** over everything ingested (`search`).

This is project #2 in the [AI ecosystem roadmap](../ROADMAP.md). It reuses the Personal
LLM package instead of reimplementing retrieval or routing.

## Setup

```powershell
cd C:\Users\Asus\projects\ai-ecosystem\second-brain
py -3.12 -m venv venv
& "venv\Scripts\python" -m pip install -r requirements.txt

# Install the Personal LLM core (the sibling package this project builds on).
# This pulls the heavier embedding/vector deps and is required to actually run the CLI.
& "venv\Scripts\python" -m pip install -e ..\personal-llm
& "venv\Scripts\python" -m pip install -e .
```

## Use

```powershell
# Ingest the bundled sample vault (or pass your own folder)
& "venv\Scripts\python" -m second_brain.interfaces.cli ingest-vault sample-vault

# Search, find related notes, and export the graph
& "venv\Scripts\python" -m second_brain.interfaces.cli search "how does retrieval work"
& "venv\Scripts\python" -m second_brain.interfaces.cli related sample-vault\recall.md
& "venv\Scripts\python" -m second_brain.interfaces.cli graph --out data\graph.html
```

Ingest and search reuse Personal LLM's local embeddings, so they work with no API key.

## Tests

```powershell
& "venv\Scripts\python" -m pytest tests/ -q
```

The core logic (vault, links, graphview) has no Personal LLM import - dependencies are
injected - so the whole suite runs fully mocked, with no API key, network, or heavy
model. Only the CLI touches the real core, and it imports it lazily.

## Architecture

```
CLI (thin, lazy-imports the core)
        |
   second_brain: vault (incremental ingest) | links (doc-level auto-linking) | graphview (offline HTML)
        |
   Personal LLM core: ingest_file | semantic_search | knowledge graph (store.all_nodes/all_edges)
```

Design docs for the full vision live in [`plan.md`](plan.md); the north-star prompt is
`C:\Users\Asus\Documents\fable 5\second brain.txt`.
