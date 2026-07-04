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
