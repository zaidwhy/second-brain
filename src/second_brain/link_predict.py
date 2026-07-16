"""Link prediction: common-neighbors baseline over the knowledge graph.

PROJECT-GENESIS sec. 9 Tier 4 item 27. graphview.py renders the graph the core already
knows about; this predicts edges it does NOT know about yet - two notes that share many
neighbors but have no direct link are the most promising "you probably want to connect
these" candidates. Common neighbors (Liben-Nowell & Kleinberg, 2003) is the standard
link-prediction baseline: chosen here over Adamic-Adar/Jaccard variants for its
zero-parameter simplicity - the score IS the shared-neighbor set, nothing to tune or
justify. Detect-candidates-for-review only, same contract as near_dup.py and
contradictions.py: this never writes an edge, only suggests one.

No Personal LLM import: `predict_links` takes duck-typed node/edge objects (personal_llm
KGNode / KGEdge in real use, same Protocol shape as graphview.py, plain fakes in tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


class _Node(Protocol):
    id: str
    name: str
    type: str


class _Edge(Protocol):
    src: str
    rel: str
    dst: str


@dataclass(frozen=True)
class LinkPrediction:
    node_a: str
    node_b: str
    score: int
    common_neighbors: frozenset[str]


def _adjacency(nodes: Iterable[_Node], edges: Iterable[_Edge]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {node.id: set() for node in nodes}
    for edge in edges:
        if edge.src not in adjacency or edge.dst not in adjacency or edge.src == edge.dst:
            continue
        adjacency[edge.src].add(edge.dst)
        adjacency[edge.dst].add(edge.src)
    return adjacency


def predict_links(
    nodes: Iterable[_Node],
    edges: Iterable[_Edge],
    *,
    k: int = 10,
    min_score: int = 1,
) -> list[LinkPrediction]:
    """Rank unconnected node pairs by shared-neighbor count, highest first.

    O(n^2) pairwise comparison over the node set, same scale as near_dup's and
    contradictions' pairwise scans - fine for a personal knowledge graph. Pairs already
    directly linked are skipped (nothing to predict); pairs below `min_score` shared
    neighbors are dropped as noise. Ties broken by node id for a deterministic order.
    """
    adjacency = _adjacency(nodes, edges)
    node_ids = sorted(adjacency)
    predictions: list[LinkPrediction] = []
    for i in range(len(node_ids)):
        node_a = node_ids[i]
        for j in range(i + 1, len(node_ids)):
            node_b = node_ids[j]
            if node_b in adjacency[node_a]:
                continue
            common = adjacency[node_a] & adjacency[node_b]
            if len(common) < min_score:
                continue
            predictions.append(LinkPrediction(node_a, node_b, len(common), frozenset(common)))
    predictions.sort(key=lambda p: (-p.score, p.node_a, p.node_b))
    return predictions[:k]
