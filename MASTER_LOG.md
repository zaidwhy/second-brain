# Second Brain++ - Master Log

Append-only. Newest entries at the bottom. Read just the tail for recent context.

## 2026-07-04 - Project created (v0.1 scaffold)

- Second project in the AI ecosystem, built on the Personal LLM core.
- Scaffolded `second_brain` package at `C:\Users\Asus\projects\ai-ecosystem\second-brain`.
- v0.1 modules: `vault` (folder-wide incremental ingest with a content-hash manifest),
  `links` (document-level auto-linking that aggregates chunk hits and drops the source note),
  `graphview` (knowledge graph to node-link JSON plus a self-contained offline HTML force graph),
  and a Typer `cli` (`ingest-vault`, `search`, `related`, `graph`) that lazy-imports the core.
- Core logic has no Personal LLM import (dependencies injected), so the test suite runs
  fully mocked. 15 tests across vault/links/graphview.
- Sample vault with 3 notes bundled for a zero-config first run.

## 2026-07-04 - Published + Graphify integration

- Created public GitHub repo `syzayd/second-brain` and pushed v0.1.
- Fixed the install docs: the core's runtime deps live in personal-llm/requirements.txt
  (its pyproject declares none), so downstream installs must `pip install -r` those too.
- Added an optional Graphify integration (https://github.com/Graphify-Labs, MIT):
  `graphify_adapter` (run the `graphify` CLI, parse its graph.json defensively, merge graphs)
  and a `code-graph` CLI command that renders a code graph in our offline viewer, optionally
  merged with the notes graph. Graphify is never vendored or required. 22 tests total.

## 2026-07-04 - Graph viewer redesign + Graphify live validation

- Redesigned the graph HTML viewer (frontend-design pass): ink/vignette ground, serif title,
  mono HUD, node color-by-type with a legend, degree-sized hubs, a hover "trace connections"
  mode with a relationship readout, an inviting empty state, and prefers-reduced-motion support.
  Fixed a temporal-dead-zone bug (dragging referenced before its let) that had blanked the canvas,
  and made labels hide on large graphs until hover to avoid clutter. Verified visually via browser
  screenshots (notes graph, empty state, and a 71-node code graph).
- Validated the Graphify integration against a real run: installed graphifyy in an isolated venv,
  ran `graphify update --no-cluster` (no LLM needed) on this repo's source, confirmed the real
  schema (nodes: id/label/file_type; links: source/target/relation/confidence), and corrected the
  adapter (map file_type -> node type; run_graphify uses `update --no-cluster` and reads graph.json
  from the target's graphify-out). Added a real-schema test. 23 tests total.
- Also verified end-to-end against the live core: ingest-vault + search + related all work with local
  embeddings; graph export needs a triple-capable LLM (empty otherwise, which the new empty state covers).

## 2026-07-04 - add-note command

- Added an `add-note "text" [--label NAME]` CLI command that ingests a single note directly via
  personal_llm.memory.ingest.ingest_text - no file needed. Verified: adds the note and it comes back
  as the top `search` hit. Note: the strongest local Ollama model present for graph triple extraction
  is qwen2.5:3b-instruct (set OLLAMA_MODEL to it; the router default llama3.2:3b tag is not installed).

## 2026-07-04 - Default the graph model to qwen2.5:3b-instruct

- Second Brain now defaults the graph's extraction model to qwen2.5:3b-instruct: added
  `ollama_model` to SecondBrainSettings and `_engine()` sets OLLAMA_MODEL via os.environ.setdefault
  (respects a user-set OLLAMA_MODEL / SECOND_BRAIN_OLLAMA_MODEL). No env var needed anymore.
- Verified with no env var set: add-note on relational text extracted 3 triples and graph rendered
  6 nodes / 3 links (civos-council had returned empty; qwen2.5:3b-instruct works).
