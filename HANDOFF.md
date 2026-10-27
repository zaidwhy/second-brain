# second-brain handoff - 2026-10-28

- Done: the ingest manifest now lives beside the vector store (see MASTER_LOG 2026-10-28); 116 tests; README plate, profile repo and PROFILE-FACTS updated (ecosystem 381).
- Open: rebuild `venv` (Python 3.12, CLAUDE.md) and run one real `ingest-vault` + `search` to confirm embeddings end to end. `tests/test_adapters.py:64` has a pre-existing ruff E731.
- The old `data/vault_manifest.json` is left in place (gitignored); delete it once the default store's copy has been used.
