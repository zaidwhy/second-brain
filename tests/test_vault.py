"""Vault ingestion: file discovery, fingerprinting, and incremental skip/force."""

from __future__ import annotations

from pathlib import Path

from second_brain.vault import (
    file_fingerprint,
    ingest_vault,
    iter_vault_files,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_iter_vault_files_filters_and_recurses(tmp_path):
    _write(tmp_path / "a.md", "one")
    _write(tmp_path / "sub" / "b.txt", "two")
    _write(tmp_path / "ignore.pyc", "nope")
    _write(tmp_path / "image.png", "binary-ish")

    found = {p.name for p in iter_vault_files(tmp_path)}
    assert found == {"a.md", "b.txt", "image.png"}


def test_iter_vault_files_missing_dir_is_empty(tmp_path):
    assert iter_vault_files(tmp_path / "nope") == []


def test_fingerprint_changes_with_content(tmp_path):
    f = tmp_path / "n.md"
    _write(f, "hello")
    first = file_fingerprint(f)
    _write(f, "hello world")
    assert file_fingerprint(f) != first


def test_ingest_vault_skips_unchanged_on_second_run(tmp_path):
    vault = tmp_path / "vault"
    _write(vault / "a.md", "alpha")
    _write(vault / "b.md", "beta")
    manifest = tmp_path / "manifest.json"

    calls: list[str] = []
    ingest_fn = lambda path: calls.append(path.name)

    first = ingest_vault(vault, manifest, ingest_fn)
    assert len(first.ingested) == 2 and len(first.skipped) == 0
    assert sorted(calls) == ["a.md", "b.md"]

    calls.clear()
    second = ingest_vault(vault, manifest, ingest_fn)
    assert len(second.ingested) == 0 and len(second.skipped) == 2
    assert calls == []


def test_ingest_vault_reingests_changed_file(tmp_path):
    vault = tmp_path / "vault"
    note = vault / "a.md"
    _write(note, "alpha")
    manifest = tmp_path / "manifest.json"

    calls: list[str] = []
    ingest_fn = lambda path: calls.append(path.name)

    ingest_vault(vault, manifest, ingest_fn)
    calls.clear()

    _write(note, "alpha changed")
    report = ingest_vault(vault, manifest, ingest_fn)
    assert report.ingested and calls == ["a.md"]


def test_ingest_vault_force_ignores_manifest(tmp_path):
    vault = tmp_path / "vault"
    _write(vault / "a.md", "alpha")
    manifest = tmp_path / "manifest.json"

    calls: list[str] = []
    ingest_fn = lambda path: calls.append(path.name)

    ingest_vault(vault, manifest, ingest_fn)
    calls.clear()

    report = ingest_vault(vault, manifest, ingest_fn, force=True)
    assert report.ingested and calls == ["a.md"]
