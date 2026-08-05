@echo off
REM One-click run parity (PROJECT-GENESIS.md Tier 6 item 43): mirrors this project's
REM entry in jarvis-launcher's jarvis.config.json ("knowledge graph" action, the
REM default for "Second Brain") verbatim, so the launcher and this repo never drift.
REM Ingests/rebuilds the knowledge graph via the CLI, then opens the rendered HTML -
REM matches CLAUDE.md's documented run command, just with the venv prefix jarvis
REM already assumes ("dir" is this repo root).
venv\Scripts\python -m second_brain.interfaces.cli graph && start data\graph.html
