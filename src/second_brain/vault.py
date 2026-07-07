"""Vault ingestion: walk a folder of notes and ingest each into the Personal LLM core.

Personal LLM ingests one file at a time. Second Brain adds folder-level, incremental
ingestion: a content-hash manifest lets re-runs skip unchanged files, so a large vault
only re-embeds what actually changed.

This module has no Personal LLM import on purpose - the caller injects `ingest_fn`, which
keeps the heavy dependencies (and the tests) out of the core logic.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf", ".png", ".jpg", ".jpeg"}

# ingest_fn takes a file path and does the real ingestion (returns anything).
IngestFn = Callable[[Path], object]


def iter_vault_files(vault_dir: Path, suffixes: set[str] | None = None) -> list[Path]:
    """All supported files under `vault_dir`, sorted for deterministic ordering."""
    suffixes = suffixes or SUPPORTED_SUFFIXES
    vault_dir = Path(vault_dir)
    if not vault_dir.exists():
        return []
    return sorted(
        p for p in vault_dir.rglob("*") if p.is_file() and p.suffix.lower() in suffixes
    )


def file_fingerprint(path: Path) -> str:
    """SHA-256 of file bytes - changes iff the content changes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class VaultManifest:
    fingerprints: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "VaultManifest":
        path = Path(path)
        if path.exists():
            return cls(json.loads(path.read_text(encoding="utf-8")))
        return cls()

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.fingerprints, indent=2), encoding="utf-8")


@dataclass
class VaultIngestReport:
    ingested: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.ingested) + len(self.skipped)


def ingest_vault(
    vault_dir: Path,
    manifest_path: Path,
    ingest_fn: IngestFn,
    *,
    force: bool = False,
) -> VaultIngestReport:
    """Ingest changed files under `vault_dir`, skipping ones whose content is unchanged.

    `ingest_fn(path)` performs the actual ingestion (wraps
    personal_llm.memory.ingest.ingest_file in real use; a stub in tests).
    """
    manifest = VaultManifest.load(manifest_path)
    report = VaultIngestReport()
    # Save inside finally: if ingest_fn raises mid-vault, files already ingested this run
    # must not be re-embedded on the next run.
    try:
        for path in iter_vault_files(vault_dir):
            key = str(path.resolve())
            fingerprint = file_fingerprint(path)
            if not force and manifest.fingerprints.get(key) == fingerprint:
                report.skipped.append(key)
                continue
            ingest_fn(path)
            manifest.fingerprints[key] = fingerprint
            report.ingested.append(key)
    finally:
        manifest.save(manifest_path)
    return report
