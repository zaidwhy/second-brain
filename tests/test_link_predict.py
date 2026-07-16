"""Link prediction: common-neighbors baseline scoring + ranking."""

from __future__ import annotations

from dataclasses import dataclass

from second_brain.link_predict import predict_links


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


def _nodes(*ids: str) -> list[FakeNode]:
    return [FakeNode(i, i, "note") for i in ids]


def test_no_prediction_without_shared_neighbors():
    nodes = _nodes("a", "b")
    edges = [FakeEdge("a", "mentions", "b")]
    assert predict_links(nodes, edges) == []


def test_predicts_pair_sharing_one_neighbor():
    # a-c and b-c linked, a-b not linked: a and b share neighbor c.
    nodes = _nodes("a", "b", "c")
    edges = [FakeEdge("a", "mentions", "c"), FakeEdge("b", "mentions", "c")]
    predictions = predict_links(nodes, edges)
    assert len(predictions) == 1
    assert (predictions[0].node_a, predictions[0].node_b) == ("a", "b")
    assert predictions[0].score == 1
    assert predictions[0].common_neighbors == frozenset({"c"})


def test_already_linked_pair_is_not_predicted():
    nodes = _nodes("a", "b", "c")
    edges = [
        FakeEdge("a", "mentions", "c"),
        FakeEdge("b", "mentions", "c"),
        FakeEdge("a", "mentions", "b"),
    ]
    assert predict_links(nodes, edges) == []


def test_self_loop_edges_are_ignored():
    nodes = _nodes("a", "b", "c")
    edges = [
        FakeEdge("a", "mentions", "a"),
        FakeEdge("a", "mentions", "c"),
        FakeEdge("b", "mentions", "c"),
    ]
    predictions = predict_links(nodes, edges)
    assert len(predictions) == 1
    assert (predictions[0].node_a, predictions[0].node_b) == ("a", "b")


def test_edges_referencing_missing_nodes_are_dropped():
    nodes = _nodes("a", "b")
    edges = [FakeEdge("a", "mentions", "ghost"), FakeEdge("b", "mentions", "ghost")]
    assert predict_links(nodes, edges) == []


def test_ranked_by_score_descending():
    # a-b share two neighbors (c, d); a-e share one (c). a-b should rank above a-e.
    nodes = _nodes("a", "b", "c", "d", "e")
    edges = [
        FakeEdge("a", "mentions", "c"),
        FakeEdge("b", "mentions", "c"),
        FakeEdge("a", "mentions", "d"),
        FakeEdge("b", "mentions", "d"),
        FakeEdge("a", "mentions", "e"),
    ]
    predictions = predict_links(nodes, edges)
    pairs = [(p.node_a, p.node_b) for p in predictions]
    assert pairs[0] == ("a", "b")
    assert predictions[0].score == 2


def test_min_score_filters_weak_candidates():
    nodes = _nodes("a", "b", "c")
    edges = [FakeEdge("a", "mentions", "c"), FakeEdge("b", "mentions", "c")]
    assert predict_links(nodes, edges, min_score=2) == []


def test_k_limits_result_count():
    # Four nodes (a,b,c,d) all sharing hub "h": C(4,2) = 6 unconnected pairs.
    nodes = _nodes("a", "b", "c", "d", "h")
    edges = [FakeEdge(n, "mentions", "h") for n in ("a", "b", "c", "d")]
    predictions = predict_links(nodes, edges, k=2)
    assert len(predictions) == 2


def test_ties_broken_by_node_id():
    nodes = _nodes("a", "b", "c", "d")
    edges = [FakeEdge(n, "mentions", "d") for n in ("a", "b", "c")]
    predictions = predict_links(nodes, edges)
    pairs = [(p.node_a, p.node_b) for p in predictions]
    assert pairs == sorted(pairs)


def test_empty_graph_returns_empty():
    assert predict_links([], []) == []
