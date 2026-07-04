# Second Brain++ - Claude Instructions

AI knowledge layer over the Personal LLM core (project #2 in `../ROADMAP.md`). Adds vault
ingestion, document-level auto-linking, and an offline knowledge-graph visualization.

## Run

```powershell
cd C:\Users\Asus\projects\ai-ecosystem\second-brain
& "venv\Scripts\python" -m second_brain.interfaces.cli --help
```

## Python environment

- Venv folder is `venv`, **Python 3.12** (matches personal-llm; torch/chromadb wheels lag on 3.14).
  `py -3.12 -m venv venv`
- Install: `& "venv\Scripts\python" -m pip install -r requirements.txt`, then the sibling
  core's runtime deps `& "venv\Scripts\python" -m pip install -r ..\personal-llm\requirements.txt`,
  then the core itself `-e ..\personal-llm`, then `-e .`. The core's pyproject declares no
  runtime deps (they are in its requirements.txt), so the editable install alone is not enough.

## Tests

```powershell
& "venv\Scripts\python" -m pytest tests/ -q
```
Core modules (`vault`, `links`, `graphview`) take injected callables/objects and have no
Personal LLM import, so tests run without heavy deps or a network. Keep it that way: put
`personal_llm` imports only inside CLI command bodies (lazy), never at module top level.

## Architecture notes

- The core does the AI work; this package only adds vault/link/graph logic on top. Reuse
  `personal_llm.memory.ingest.ingest_file`, `personal_llm.memory.retrieve.semantic_search`,
  and `store.all_nodes()/all_edges()` rather than reimplementing them.
- `graphview.render_html` must stay fully self-contained (no CDN, no external fonts/scripts).

## Gotchas

- Never use the em dash character (U+2014) anywhere; use " - " instead. In tests that must
  reference it, use `chr(0x2014)`, not the literal.
- `data/` is gitignored and ephemeral (manifest, exported graph.html). The Personal LLM
  memory/vector stores live in the personal-llm repo's `data/`, not here.
