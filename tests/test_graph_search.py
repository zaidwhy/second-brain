"""Graph node search/filter: pure query over a fixture node/link list."""

from __future__ import annotations

from dataclasses import dataclass

from second_brain.graph_search import search_nodes


@dataclass(frozen=True)
class FakeNode:
    id: str
    name: str
    type: str


@dataclass(frozen=True)
class FakeEdge:
    src: str
    rel: str
    dst: str


def _graph():
    nodes = [
        FakeNode("1", "Second Brain Roadmap", "note"),
        FakeNode("2", "Personal LLM Router", "note"),
        FakeNode("3", "Zaid Ali Syed", "person"),
        FakeNode("4", "DreamOS Pulse", "note"),
    ]
    edges = [
        FakeEdge("1", "mentions", "3"),
        FakeEdge("2", "mentions", "3"),
        FakeEdge("2", "mentions", "1"),
    ]
    return nodes, edges


def test_no_query_or_type_returns_every_node_ranked_by_degree():
    nodes, edges = _graph()
    results = search_nodes(nodes, edges)
    # "1", "2", "3" all have degree 2; ties break alphabetically by name
    # ("Personal LLM Router" < "Second Brain Roadmap" < "Zaid Ali Syed").
    assert [r.node.id for r in results] == ["2", "1", "3", "4"]
    assert [r.degree for r in results] == [2, 2, 2, 0]


def test_query_filters_by_case_insensitive_name_substring():
    nodes, edges = _graph()
    results = search_nodes(nodes, edges, query="pulse")
    assert [r.node.id for r in results] == ["4"]


def test_query_matches_partial_word_anywhere_in_name():
    nodes, edges = _graph()
    results = search_nodes(nodes, edges, query="brain")
    assert [r.node.id for r in results] == ["1"]


def test_type_filters_to_exact_match():
    nodes, edges = _graph()
    results = search_nodes(nodes, edges, type="person")
    assert [r.node.id for r in results] == ["3"]


def test_query_and_type_combine_as_and():
    nodes, edges = _graph()
    results = search_nodes(nodes, edges, query="pulse", type="person")
    assert results == []


def test_no_match_returns_empty_list():
    nodes, edges = _graph()
    assert search_nodes(nodes, edges, query="nonexistent") == []


def test_degree_ties_broken_by_name():
    nodes, edges = _graph()
    results = search_nodes(nodes, edges, type="note")
    # "1" and "2" both have degree 2; name order breaks the tie
    # ("Personal LLM Router" < "Second Brain Roadmap").
    assert [r.node.id for r in results] == ["2", "1", "4"]


def test_self_loop_edge_counts_once_toward_degree():
    nodes = [FakeNode("a", "Alpha", "note")]
    edges = [FakeEdge("a", "self", "a")]
    results = search_nodes(nodes, edges)
    assert results[0].degree == 1


def test_edge_to_unknown_node_is_ignored():
    nodes = [FakeNode("a", "Alpha", "note")]
    edges = [FakeEdge("a", "mentions", "missing")]
    results = search_nodes(nodes, edges)
    assert results[0].degree == 1
