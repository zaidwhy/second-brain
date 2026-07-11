# Contributing

Thanks for looking at Second Brain++. It is a personal project, but issues and small,
focused PRs are welcome.

## Ground rules

1. **Tests stay offline and keyless.** The core logic modules (`vault`, `links`,
   `graphview`, `near_dup`, `contradictions`) take injected callables/objects and have
   no `personal_llm` import at module top level - keep it that way, and inject fakes in
   tests rather than adding a real dependency or a network call. A PR that adds a
   networked or model-backed test will be asked to mock it.
2. **`personal_llm` imports stay lazy.** Only import the Personal LLM core inside CLI
   command bodies (`src/second_brain/interfaces/`), never at module top level elsewhere
   - that is what keeps the core test suite fast and dependency-light.
3. **Reuse the core, don't reimplement it.** Ingestion, retrieval, and knowledge-graph
   storage already exist in `personal_llm` (`memory.ingest.ingest_file`,
   `memory.retrieve.semantic_search`, `store.all_nodes()`/`all_edges()`). Build on top
   of them instead of duplicating that logic here.
4. **`graphview.render_html` stays fully self-contained.** No CDN, no external fonts or
   scripts - the exported graph must open and work offline, from a single file.
5. **One concern per PR.** Small and surgical beats broad and clever.

## Dev setup

Follow the Quickstart in [README.md](README.md) (Python 3.12, plus the sibling
`personal-llm` core installed alongside it), then:

```powershell
& "venv\Scripts\python" -m pytest tests/ -q
```

All tests should pass before and after your change. CI runs the same command on every
push and PR.

## Design context

The full vision and phase plan live in [`plan.md`](plan.md). If your change alters
scope or direction, update it in the same PR.
