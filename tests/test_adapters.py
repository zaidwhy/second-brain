"""Ingestion adapter contract: MarkdownAdapter's suffix discrimination, the
IngestAdapter Protocol being satisfiable by an unrelated class, and ingest_vault's
adapter dispatch / fallback behavior."""

from __future__ import annotations

from pathlib import Path

from second_brain.adapters import DEFAULT_ADAPTERS, IngestAdapter, MarkdownAdapter, find_adapter
from second_brain.vault import ingest_vault


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_markdown_adapter_handles_md_and_txt_not_others():
    adapter = MarkdownAdapter()
    assert adapter.handles(Path("note.md"))
    assert adapter.handles(Path("note.MARKDOWN"))  # case-insensitive, like vault.py
    assert adapter.handles(Path("note.txt"))
    assert not adapter.handles(Path("scan.pdf"))
    assert not adapter.handles(Path("photo.png"))


def test_markdown_adapter_ingest_delegates_to_ingest_fn():
    calls: list[Path] = []
    adapter = MarkdownAdapter()
    result = adapter.ingest(Path("note.md"), lambda p: calls.append(p) or "ok")
    assert calls == [Path("note.md")]
    assert result == "ok"


class FakePdfAdapter:
    """Minimal second adapter proving the interface isn't tied to MarkdownAdapter -
    satisfies IngestAdapter via structural typing (a Protocol), no shared base class."""

    def handles(self, path: Path) -> bool:
        return Path(path).suffix.lower() == ".pdf"

    def ingest(self, path: Path, ingest_fn):
        return ingest_fn(path)


def test_fake_adapter_satisfies_the_protocol():
    assert isinstance(FakePdfAdapter(), IngestAdapter)
    assert isinstance(MarkdownAdapter(), IngestAdapter)


def test_find_adapter_picks_first_match_and_none_when_unhandled():
    adapters = (MarkdownAdapter(), FakePdfAdapter())
    assert isinstance(find_adapter(Path("a.md"), adapters), MarkdownAdapter)
    assert isinstance(find_adapter(Path("a.pdf"), adapters), FakePdfAdapter)
    assert find_adapter(Path("a.png"), adapters) is None


def test_ingest_vault_routes_markdown_through_adapter_with_no_behavior_change(tmp_path):
    vault = tmp_path / "vault"
    _write(vault / "a.md", "alpha")
    manifest = tmp_path / "manifest.json"

    calls: list[str] = []
    ingest_fn = lambda path: calls.append(path.name)

    report = ingest_vault(vault, manifest, ingest_fn)
    assert report.ingested and calls == ["a.md"]
    assert DEFAULT_ADAPTERS == (DEFAULT_ADAPTERS[0],)  # sanity: still markdown-only today


def test_ingest_vault_falls_back_to_ingest_fn_for_unadapted_suffix(tmp_path):
    """.png has no adapter yet - ingest_vault must still call ingest_fn directly,
    exactly like every suffix did before adapters existed."""
    vault = tmp_path / "vault"
    _write(vault / "photo.png", "binary-ish")
    manifest = tmp_path / "manifest.json"

    calls: list[str] = []
    ingest_fn = lambda path: calls.append(path.name)

    report = ingest_vault(vault, manifest, ingest_fn)
    assert report.ingested == [str((vault / "photo.png").resolve())]
    assert calls == ["photo.png"]


def test_ingest_vault_accepts_custom_adapters(tmp_path):
    vault = tmp_path / "vault"
    _write(vault / "doc.pdf", "%PDF-fake")
    manifest = tmp_path / "manifest.json"

    calls: list[str] = []
    ingest_fn = lambda path: calls.append(path.name)

    report = ingest_vault(vault, manifest, ingest_fn, adapters=(FakePdfAdapter(),))
    assert report.ingested and calls == ["doc.pdf"]
