"""Ingestion adapter interface: per-file-type handlers for vault ingestion.

`vault.py` walks a vault directory and, for every supported file, delegates the actual
Personal LLM ingestion to an injected `ingest_fn`. Previously every suffix went through
that same function uniformly, with no per-file-type distinction anywhere in the code.
This module gives that implicit behavior an explicit seam: an `IngestAdapter` declares
which suffixes it owns and how a matching file becomes an ingest call, so future file
types (PDFs, images) can be adapted differently later instead of being folded into the
same code path as markdown.

Like `vault.py`, this module has no Personal LLM import at module level. Adapters still
delegate to a caller-injected `ingest_fn` for the actual embedding/store call - see
docs/ADAPTERS.md for the full contract and how to add a new adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

# Same shape as vault.IngestFn: takes a file path, performs the real ingestion, returns
# whatever the caller's ingest pipeline returns. Kept as a separate alias (rather than an
# import from vault) so this module has no dependency on vault.py either.
IngestFn = Callable[[Path], object]


@runtime_checkable
class IngestAdapter(Protocol):
    """Contract for a per-file-type ingestion adapter.

    Implementations declare which suffixes they are responsible for (`handles`) and how
    a matching file is turned into an ingest call (`ingest`). `ingest` receives the
    caller's `ingest_fn` so an adapter never needs to import `personal_llm` itself - it
    stays a pure dispatch-plus-optional-preprocessing layer, matching this repo's rule
    that `personal_llm` imports live only inside CLI command bodies.
    """

    def handles(self, path: Path) -> bool:
        """Return True if this adapter is responsible for `path`."""
        ...

    def ingest(self, path: Path, ingest_fn: IngestFn) -> object:
        """Turn `path` into an ingest call, returning whatever `ingest_fn` returns."""
        ...


class MarkdownAdapter:
    """Adapter for plain-text notes: markdown and `.txt`.

    Markdown and plain text need no preprocessing before ingestion, so this adapter just
    forwards the raw path to `ingest_fn` - identical to how vault.py called `ingest_fn`
    for every suffix before this refactor.
    """

    SUFFIXES = {".md", ".markdown", ".txt"}

    def handles(self, path: Path) -> bool:
        return Path(path).suffix.lower() in self.SUFFIXES

    def ingest(self, path: Path, ingest_fn: IngestFn) -> object:
        return ingest_fn(path)


# Adapters vault.py uses by default, in priority order. Suffixes with no matching adapter
# (currently .pdf/.png/.jpg/.jpeg - recognized by vault.SUPPORTED_SUFFIXES but not yet
# adapted distinctly) fall back to calling ingest_fn directly; see docs/ADAPTERS.md.
DEFAULT_ADAPTERS: tuple[IngestAdapter, ...] = (MarkdownAdapter(),)


def find_adapter(path: Path, adapters: tuple[IngestAdapter, ...]) -> IngestAdapter | None:
    """First adapter in `adapters` whose `handles(path)` is True, or None."""
    for adapter in adapters:
        if adapter.handles(path):
            return adapter
    return None
