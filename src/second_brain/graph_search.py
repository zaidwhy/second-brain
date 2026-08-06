"""Graph node search/filter: pure query over the knowledge graph's node/link list.

PROJECT-GENESIS sec. 9 Tier 9 item 80. graphview.py renders the whole graph; a growing
vault makes that graph too large to eyeball, so this filters it down to a name/type
query - same duck-typed node/edge contract as graphview.py and link_predict.py
(personal_llm KGNode / KGEdge in real use, plain fakes in tests). Read-only: it never
mutates the graph, only ranks and returns a subset of it.
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
class GraphSearchResult:
    node: _Node
    degree: int


def _degree_by_id(nodes: Iterable[_Node], edges: Iterable[_Edge]) -> dict[str, int]:
    degree = {node.id: 0 for node in nodes}
    for edge in edges:
        if edge.src in degree:
            degree[edge.src] += 1
        if edge.dst in degree and edge.dst != edge.src:
            degree[edge.dst] += 1
    return degree


def search_nodes(
    nodes: Iterable[_Node],
    edges: Iterable[_Edge],
    *,
    query: str | None = None,
    type: str | None = None,
) -> list[GraphSearchResult]:
    """Filter nodes by a case-insensitive name substring and/or an exact type match.

    Both `query` and `type` are optional; passing neither ranks every node. Results are
    sorted by degree (most-connected first) then name, so the most relevant matches in a
    large graph surface first - same "detect/filter, never mutate" contract as
    predict_links and near_dup's clustering.
    """
    node_list = list(nodes)
    degree = _degree_by_id(node_list, edges)
    query_lower = query.lower() if query else None

    results = []
    for node in node_list:
        if query_lower is not None and query_lower not in node.name.lower():
            continue
        if type is not None and node.type != type:
            continue
        results.append(GraphSearchResult(node=node, degree=degree[node.id]))

    results.sort(key=lambda r: (-r.degree, r.node.name))
    return results
