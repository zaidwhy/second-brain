"""Tests for run.cmd (PROJECT-GENESIS.md Tier 6 item 43: one-click run parity).

Static-content checks only - run.cmd is a Windows batch script and this suite runs on
Linux CI, so it asserts the script's shape rather than executing it.
"""
from __future__ import annotations

from pathlib import Path

RUN_CMD = Path(__file__).resolve().parents[1] / "run.cmd"


def _text() -> str:
    return RUN_CMD.read_text(encoding="utf-8")


def test_run_cmd_exists():
    assert RUN_CMD.is_file()


def test_matches_jarvis_config_knowledge_graph_action():
    text = _text()
    assert "venv\\Scripts\\python -m second_brain.interfaces.cli graph" in text
    assert "start data\\graph.html" in text


def test_no_nested_quoting():
    """Mirrors the exact bug class jarvis-launcher's launcher rewrite fixed: a quote
    nested inside a quoted string makes cmd execute the literal, corrupted text."""
    for line in _text().splitlines():
        if "cmd /k" not in line and "cmd /c" not in line:
            continue
        assert '\\"' not in line, f"escaped quote (nesting) found in: {line!r}"
        assert '""' not in line, f"doubled quote (nesting) found in: {line!r}"
        opens = line.count('"')
        assert opens % 2 == 0, f"unbalanced quotes in: {line!r}"
