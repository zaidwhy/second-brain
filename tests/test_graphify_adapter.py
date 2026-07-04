"""Graphify adapter: defensive JSON parsing, merging, and the not-installed guard."""

from __future__ import annotations

import json

import pytest

from second_brain import graphify_adapter as ga


def test_parse_canonical_keys():
    data = {
        "nodes": [{"id": "a", "name": "Alpha", "type": "module"}, {"id": "b", "name": "Beta", "type": "class"}],
        "edges": [{"source": "a", "target": "b", "rel": "imports"}],
    }
    nl = ga.parse_graphify_json(data)
    assert len(nl.nodes) == 2 and len(nl.links) == 1
    assert nl.links[0] == {"source": "a", "target": "b", "rel": "imports"}


def test_parse_alias_keys():
    # Graphify may emit different key names; the parser accepts common aliases.
    data = {
        "nodes": [{"key": "a", "label": "Alpha", "kind": "module"}, {"key": "b", "title": "Beta"}],
        "links": [{"from": "a", "to": "b", "relation": "calls"}],
    }
    nl = ga.parse_graphify_json(data)
    ids = {n["id"] for n in nl.nodes}
    assert ids == {"a", "b"}
    assert nl.nodes[0]["name"] == "Alpha" and nl.nodes[0]["type"] == "module"
    assert nl.nodes[1]["name"] == "Beta" and nl.nodes[1]["type"] == "node"  # default
    assert nl.links[0] == {"source": "a", "target": "b", "rel": "calls"}


def test_parse_drops_dangling_edges():
    data = {"nodes": [{"id": "a"}], "edges": [{"source": "a", "target": "ghost"}]}
    nl = ga.parse_graphify_json(data)
    assert nl.links == []


def test_parse_empty_graph():
    nl = ga.parse_graphify_json({})
    assert nl.nodes == [] and nl.links == []


def test_load_graphify_graph_reads_file(tmp_path):
    path = tmp_path / "graph.json"
    path.write_text(json.dumps({"nodes": [{"id": "x", "name": "X"}], "edges": []}), encoding="utf-8")
    nl = ga.load_graphify_graph(path)
    assert nl.nodes[0]["id"] == "x"


def test_merge_dedupes_nodes_and_edges():
    from second_brain.graphview import NodeLink

    g1 = NodeLink(nodes=[{"id": "a", "name": "A", "type": "t"}], links=[{"source": "a", "target": "a", "rel": "self"}])
    g2 = NodeLink(
        nodes=[{"id": "a", "name": "A", "type": "t"}, {"id": "b", "name": "B", "type": "t"}],
        links=[{"source": "a", "target": "a", "rel": "self"}, {"source": "a", "target": "b", "rel": "x"}],
    )
    merged = ga.merge(g1, g2)
    assert {n["id"] for n in merged.nodes} == {"a", "b"}
    assert len(merged.links) == 2


def test_parse_real_graphify_schema():
    # Shape captured from a real `graphify update --no-cluster` run: nodes use id/label/
    # file_type; links use source/target/relation/confidence under the "links" key.
    data = {
        "input_tokens": 0,
        "output_tokens": 0,
        "nodes": [
            {"id": "init", "label": "__init__.py", "file_type": "code", "source_file": "__init__.py"},
            {"id": "vault", "label": "vault.py", "file_type": "code"},
        ],
        "links": [
            {"source": "init", "target": "vault", "relation": "imports", "confidence": "EXTRACTED", "weight": 1.0},
        ],
    }
    nl = ga.parse_graphify_json(data)
    assert {n["id"] for n in nl.nodes} == {"init", "vault"}
    assert nl.nodes[0]["name"] == "__init__.py"
    assert nl.nodes[0]["type"] == "code"  # file_type, not the filename label
    assert nl.links[0] == {"source": "init", "target": "vault", "rel": "imports"}


def test_run_graphify_raises_when_not_installed(monkeypatch):
    monkeypatch.setattr(ga.shutil, "which", lambda _name: None)
    assert ga.graphify_available() is False
    with pytest.raises(ga.GraphifyNotInstalled):
        ga.run_graphify(".")
