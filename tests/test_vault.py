"""Vault ingestion: file discovery, fingerprinting, and incremental skip/force."""

from __future__ import annotations

from pathlib import Path

from second_brain.vault import (
    file_fingerprint,
    ingest_vault,
    iter_vault_files,
    resolve_manifest_path,
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


def test_ingest_failure_still_saves_progress(tmp_path):
    """Files ingested before a mid-run crash must not be re-ingested next run."""
    _write(tmp_path / "vault" / "a.md", "one")
    _write(tmp_path / "vault" / "b.md", "two")
    manifest = tmp_path / "manifest.json"

    calls: list[str] = []

    def flaky(path: Path):
        calls.append(path.name)
        if path.name == "b.md":
            raise RuntimeError("embedder died")

    try:
        ingest_vault(tmp_path / "vault", manifest, flaky)
    except RuntimeError:
        pass
    assert calls == ["a.md", "b.md"]

    calls.clear()
    try:
        ingest_vault(tmp_path / "vault", manifest, flaky)
    except RuntimeError:
        pass
    assert calls == ["b.md"]  # a.md was remembered despite the crash


def test_manifest_defaults_to_the_data_root_the_vectors_use(tmp_path):
    root = tmp_path / "store"
    path = resolve_manifest_path(None, root, legacy=tmp_path / "old" / "vault_manifest.json")
    assert path == root / "vault_manifest.json"


def test_an_explicit_manifest_path_wins(tmp_path):
    chosen = tmp_path / "mine.json"
    assert resolve_manifest_path(chosen, tmp_path / "store", legacy=tmp_path / "old.json") == chosen


def test_legacy_manifest_is_copied_once_so_nothing_is_re_embedded(tmp_path):
    legacy = tmp_path / "old" / "vault_manifest.json"
    _write(legacy, '{"a.md": "abc"}')
    path = resolve_manifest_path(None, tmp_path / "store", legacy=legacy)
    assert path.read_text(encoding="utf-8") == '{"a.md": "abc"}'


def test_legacy_manifest_never_overwrites_the_current_one(tmp_path):
    legacy = tmp_path / "old" / "vault_manifest.json"
    _write(legacy, '{"stale": "1"}')
    current = tmp_path / "store" / "vault_manifest.json"
    _write(current, '{"fresh": "2"}')
    resolve_manifest_path(None, tmp_path / "store", legacy=legacy)
    assert current.read_text(encoding="utf-8") == '{"fresh": "2"}'


def test_a_new_store_with_an_old_manifest_elsewhere_still_ingests(tmp_path):
    # The bug: the manifest sat in a cwd-relative data/ folder while vectors followed
    # NEXUS_DATA_DIR, so a fresh store skipped every note and stayed empty.
    vault = tmp_path / "vault"
    _write(vault / "a.md", "one")
    old_store_manifest = tmp_path / "old-store" / "vault_manifest.json"
    ingest_vault(vault, old_store_manifest, lambda _p: None)
    new_manifest = resolve_manifest_path(None, tmp_path / "new-store", legacy=tmp_path / "absent.json")
    seen: list[Path] = []
    report = ingest_vault(vault, new_manifest, seen.append)
    assert len(report.ingested) == 1 and len(seen) == 1


def test_no_legacy_means_no_copy_into_a_different_store(tmp_path):
    path = resolve_manifest_path(None, tmp_path / "other-store", legacy=None)
    assert not path.exists()
