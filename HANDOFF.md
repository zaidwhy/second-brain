# second-brain handoff - 2026-10-28

- Done: the ingest manifest now lives beside the vector store (see MASTER_LOG 2026-10-28); 116 tests; README plate, profile repo and PROFILE-FACTS updated (ecosystem 381).
- Done 2026-10-28: `venv` rebuilt (Python 3.12, torch 2.14.1), 116 tests pass in it. Real run with `NEXUS_DATA_DIR` on a scratch folder and a 3-note vault: first `ingest-vault` ingested 3 (59 s, first model load), a second run skipped 3, `vault_manifest.json` landed in the custom data root, and a fresh second data root ingested all 3 again (no legacy manifest copied). `search "how hot should the water be"` ranked tea.md first (0.489).
- Open: `tests/test_adapters.py:64` has a pre-existing ruff E731.
- The old `data/vault_manifest.json` is left in place (gitignored); delete it once the default store's copy has been used.
