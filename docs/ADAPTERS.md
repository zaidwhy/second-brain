# Ingestion adapters

`vault.py` walks a vault directory, fingerprints each file, and skips ones whose content
hasn't changed. What actually happens to a *changed* file is dispatched through the
`IngestAdapter` interface in `src/second_brain/adapters.py`.

## The interface

```python
class IngestAdapter(Protocol):
    def handles(self, path: Path) -> bool: ...
    def ingest(self, path: Path, ingest_fn: IngestFn) -> object: ...
```

- `handles(path)` - True if this adapter owns files with this path (in practice, this
  suffix).
- `ingest(path, ingest_fn)` - turns the file into an ingest call. `ingest_fn` is the same
  caller-injected callable `ingest_vault` has always taken (in real use it wraps
  `personal_llm.memory.ingest.ingest_file`; tests pass a stub). An adapter may do
  file-type-specific preprocessing (e.g. OCR, PDF text extraction) before calling
  `ingest_fn`, or call it straight through.

`IngestAdapter` is a `typing.Protocol`, so any object with matching `handles`/`ingest`
methods satisfies it - no base class to inherit from required, though nothing stops an
adapter from also being a dataclass or a plain class with state (e.g. a cache).

**No `personal_llm` import at module level.** Same rule as `vault.py`: adapters must not
import `personal_llm` at the top of `adapters.py` or any adapter module. They receive
`ingest_fn` from the caller and call it - the caller (a CLI command body, or a test) is
where `personal_llm` gets imported.

## How `ingest_vault` uses adapters

`ingest_vault(..., adapters=DEFAULT_ADAPTERS)` looks up the first adapter in `adapters`
whose `handles(path)` returns True and calls `adapter.ingest(path, ingest_fn)`. If no
adapter handles a path, `ingest_vault` falls back to calling `ingest_fn(path)` directly -
this is exactly what happened for every file before adapters existed, so any suffix
without a dedicated adapter keeps its old behavior unchanged.

## Today's adapters

- `MarkdownAdapter` - handles `.md` and `.markdown` (also `.txt`, since plain text needs
  the same no-preprocessing treatment). `ingest()` just calls `ingest_fn(path)`; there is
  no markdown-specific preprocessing yet.

## Suffixes recognized but not yet adapted

`vault.SUPPORTED_SUFFIXES` also includes `.pdf`, `.png`, `.jpg`, and `.jpeg`. No adapter
handles them yet, so they take the fallback path (`ingest_fn(path)` directly, same as
before this refactor). This is a deliberate seam for future work:

- A `PdfAdapter` could extract text (e.g. via `pypdf`) before handing something ingestible
  to `ingest_fn`, instead of relying on `ingest_fn` to open a raw PDF path itself.
- An `ImageAdapter` could run OCR or a vision-model captioning step first.

Either adapter would live in `adapters.py` (or a new module importing from it) with heavy
dependencies imported lazily inside `ingest()`, matching this repo's "no heavy imports at
module level" rule.

## Adding a new adapter

1. Write a class with `handles(path) -> bool` and `ingest(path, ingest_fn) -> object`.
   Keep any heavy/`personal_llm` imports inside `ingest()`, not at module level.
2. Add it to the tuple passed as `adapters=` when calling `ingest_vault` (or extend
   `DEFAULT_ADAPTERS` if it should apply everywhere). Order matters: the first adapter
   whose `handles()` returns True wins, so put more specific adapters before general ones.
3. Add a test using a fake `ingest_fn` (see `tests/test_vault.py` for the pattern) -
   no `personal_llm` or network dependency needed.
