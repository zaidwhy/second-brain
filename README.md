# Second Brain++

**Your Mind. Expanded.** An AI knowledge layer built on top of the [Personal LLM](../personal-llm) core.

Personal LLM already gives us memory, RAG, and a knowledge graph. Second Brain++ adds the
vault-level workflows the core does not:

- **Vault ingestion** - point it at a folder of notes and it ingests every changed file,
  skipping unchanged ones via a content-hash manifest (`ingest-vault`).
- **Quick note** - drop a single note straight in from the command line, no file needed
  (`add-note "..."`).
- **Auto-linking** - given a note, surface the most related *other* notes, aggregated at
  the document level rather than as raw chunks (`related`).
- **Knowledge-graph view** - export the graph to a single self-contained, offline HTML
  visualization with an inline force layout, no CDN (`graph`).
- **Semantic search** over everything ingested (`search`).
- **Code graphs via Graphify** (optional) - build a code/repo knowledge graph with
  [Graphify](https://github.com/Graphify-Labs) and render it in the same offline viewer,
  optionally merged with your notes graph (`code-graph`).

This is project #2 in the [AI ecosystem roadmap](../ROADMAP.md). It reuses the Personal
LLM package instead of reimplementing retrieval or routing.

> **One-click run:** the ecosystem launcher one level up (`..\run.cmd`) tests and demos this
> project alongside Personal LLM in a single command, and opens the knowledge graph for you.
> Double-click it for a menu, or run `..\run.cmd demo`.

## Setup

```powershell
cd C:\Users\Asus\projects\ai-ecosystem\second-brain
py -3.12 -m venv venv
& "venv\Scripts\python" -m pip install -r requirements.txt

# Install the Personal LLM core (the sibling package this project builds on).
# Its runtime deps (chromadb, sentence-transformers, etc.) live in its requirements.txt,
# not its pyproject, so install both: the deps, then the editable package.
& "venv\Scripts\python" -m pip install -r ..\personal-llm\requirements.txt
& "venv\Scripts\python" -m pip install -e ..\personal-llm
& "venv\Scripts\python" -m pip install -e .
```

## Use

```powershell
# Ingest the bundled sample vault (or pass your own folder)
& "venv\Scripts\python" -m second_brain.interfaces.cli ingest-vault sample-vault

# Or drop in a single note without a file:
& "venv\Scripts\python" -m second_brain.interfaces.cli add-note "Remember: qwen2.5:3b-instruct is the best local model for the graph" --label idea

# Search, find related notes, and export the graph
& "venv\Scripts\python" -m second_brain.interfaces.cli search "how does retrieval work"
& "venv\Scripts\python" -m second_brain.interfaces.cli related sample-vault\recall.md
& "venv\Scripts\python" -m second_brain.interfaces.cli graph --out data\graph.html

# Optional: a code graph of any repo via Graphify (pip install graphifyy first)
& "venv\Scripts\python" -m second_brain.interfaces.cli code-graph . --merge-notes
```

Ingest and search reuse Personal LLM's local embeddings, so they work with no API key.

The knowledge graph needs a chat model to extract relationships. Second Brain defaults to the
local `qwen2.5:3b-instruct` Ollama model, so `graph` populates out of the box once you have
it: `ollama pull qwen2.5:3b-instruct`. Override with `OLLAMA_MODEL` (or
`SECOND_BRAIN_OLLAMA_MODEL`) to use a different local model, or add a Gemini key to use Gemini.

## Graphify integration (optional)

`code-graph` shells out to the [Graphify](https://github.com/Graphify-Labs) CLI (MIT) to
turn a codebase into a knowledge graph, then renders Graphify's `graph.json` with our own
offline viewer - and can merge it with the notes graph via `--merge-notes`.

- By default it runs Graphify's tree-sitter extraction (`graphify update --no-cluster`),
  which needs **no LLM or API key**. Pass `--full` for Graphify's LLM community clustering
  (that path needs a provider key).
- Graphify writes its own `graphify-out/` cache into the directory it analyzes; that folder
  is gitignored here.
- Graphify is never vendored or required; install it separately with `pip install graphifyy`
  (the CLI stays `graphify`).

The adapter in `src/second_brain/graphify_adapter.py` parses Graphify's JSON defensively
(node `id`/`label`/`file_type`, links under `links` with `source`/`target`/`relation`) and
is verified against a real Graphify run, so it tolerates key-name changes across versions.

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
