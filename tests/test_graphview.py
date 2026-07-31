"""Graph view: node-link conversion, dangling-edge filtering, and self-contained HTML."""

from __future__ import annotations

from dataclasses import dataclass

from second_brain.graphview import render_html, to_nodelink


@dataclass
class FakeNode:
    id: str
    name: str
    type: str


@dataclass
class FakeEdge:
    src: str
    rel: str
    dst: str


def test_to_nodelink_basic():
    nodes = [FakeNode("1", "Zaid", "entity"), FakeNode("2", "Recall", "project")]
    edges = [FakeEdge("1", "builds", "2")]
    nl = to_nodelink(nodes, edges)
    assert len(nl.nodes) == 2 and len(nl.links) == 1
    assert nl.links[0] == {"source": "1", "target": "2", "rel": "builds"}


def test_to_nodelink_drops_dangling_edges():
    nodes = [FakeNode("1", "A", "entity")]
    edges = [FakeEdge("1", "rel", "missing")]
    nl = to_nodelink(nodes, edges)
    assert nl.links == []


def test_render_html_is_self_contained_and_embeds_data():
    nodes = [FakeNode("1", "Zaid", "entity"), FakeNode("2", "Recall", "project")]
    edges = [FakeEdge("1", "builds", "2")]
    html = render_html(to_nodelink(nodes, edges), title="My Graph")

    assert html.lstrip().startswith("<!doctype html>")
    assert "My Graph" in html
    assert '"Zaid"' in html and '"Recall"' in html
    # No external resources - fully offline.
    assert "http://" not in html and "https://" not in html
    # No unresolved template tokens.
    assert "__DATA__" not in html and "__TITLE__" not in html


def test_render_html_has_no_em_dash():
    html = render_html(to_nodelink([], []))
    assert chr(0x2014) not in html


def test_render_html_script_safe_names():
    """A node named like a closing script tag must not break out of the inline script."""
    from second_brain.graphview import NodeLink, render_html

    nl = NodeLink(nodes=[{"id": "x", "name": "</script><b>boom</b>", "type": "note"}], links=[])
    html = render_html(nl)
    assert "</script><b>boom</b>" not in html
    assert "<\/script>" in html


def test_accent_rgb_is_single_sourced():
    """The canvas focus-ring and active-edge colors must derive from one ACCENT_RGB
    constant matching CSS --accent (#e8b768), not two independently hardcoded literals
    (see docs/DESIGN.md "Known inconsistencies" / "Polish fix in this pass")."""
    html = render_html(to_nodelink([], []))
    assert "--accent: #e8b768;" in html
    assert 'const ACCENT_RGB = "232, 183, 104";' in html
    # The raw RGB triple appears exactly once now: inside the ACCENT_RGB declaration
    # itself. The two canvas draw calls reference the constant instead of retyping it.
    assert html.count("232, 183, 104") == 1
    # The bare hex form must no longer be hardcoded as a strokeStyle literal in the canvas
    # script (it still appears in the CSS declaration and the ACCENT_RGB comment above it).
    assert 'strokeStyle = "#e8b768"' not in html
