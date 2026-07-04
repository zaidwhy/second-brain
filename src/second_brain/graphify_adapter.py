"""Optional integration with Graphify (https://github.com/Graphify-Labs, MIT).

Graphify turns a codebase, docs, or media into a knowledge graph (`graphify-out/graph.json`).
Second Brain treats it as an optional external tool - like the Personal LLM core treats
Gmail/Drive via MCP - so this repo never vendors Graphify's code or hard-depends on it.

This module does two things:
- `run_graphify(...)`: shell out to the `graphify` CLI (if installed) to build a graph.
- `parse_graphify_json(...)`: convert Graphify's graph.json into our own NodeLink, so a
  code graph can be rendered with Second Brain's self-contained offline viewer and merged
  with the notes graph.

Install Graphify to use it: `pip install graphifyy` (the CLI stays `graphify`).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from second_brain.graphview import NodeLink

# Graphify's JSON may use any of these keys; we accept the common aliases defensively.
_ID_KEYS = ("id", "key", "name")
_NAME_KEYS = ("label", "name", "title", "id")
_TYPE_KEYS = ("type", "kind", "group", "category", "label")
_EDGE_LIST_KEYS = ("edges", "links", "relationships", "relations")
_SRC_KEYS = ("source", "src", "from", "start", "subject")
_DST_KEYS = ("target", "dst", "to", "end", "object")
_REL_KEYS = ("rel", "relation", "type", "label", "kind")


class GraphifyNotInstalled(RuntimeError):
    """Raised when the `graphify` CLI is not on PATH."""


def graphify_available() -> bool:
    return shutil.which("graphify") is not None


def _first(mapping: dict, keys: tuple[str, ...], default=None):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def parse_graphify_json(data: dict) -> NodeLink:
    """Convert a loaded Graphify graph.json into our NodeLink, tolerating key-name variance."""
    raw_nodes = data.get("nodes") or []
    raw_edges = []
    for key in _EDGE_LIST_KEYS:
        if isinstance(data.get(key), list):
            raw_edges = data[key]
            break

    nodes: list[dict] = []
    ids: set[str] = set()
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            continue
        node_id = _first(raw, _ID_KEYS)
        if node_id is None:
            continue
        node_id = str(node_id)
        ids.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "name": str(_first(raw, _NAME_KEYS, node_id)),
                "type": str(_first(raw, _TYPE_KEYS, "node")),
            }
        )

    links: list[dict] = []
    for raw in raw_edges:
        if not isinstance(raw, dict):
            continue
        src = _first(raw, _SRC_KEYS)
        dst = _first(raw, _DST_KEYS)
        if src is None or dst is None:
            continue
        src, dst = str(src), str(dst)
        if src in ids and dst in ids:
            links.append({"source": src, "target": dst, "rel": str(_first(raw, _REL_KEYS, ""))})

    return NodeLink(nodes=nodes, links=links)


def load_graphify_graph(json_path: Path) -> NodeLink:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return parse_graphify_json(data)


def run_graphify(target: str, out_dir: Path, mode: str | None = None, timeout: int = 1800) -> Path:
    """Run the `graphify` CLI over `target`, writing into `out_dir/graphify-out/`.

    Returns the path to the produced graph.json. Raises GraphifyNotInstalled if the CLI is
    missing, or CalledProcessError if Graphify itself fails.
    """
    if not graphify_available():
        raise GraphifyNotInstalled(
            "The `graphify` CLI was not found. Install it with `pip install graphifyy`."
        )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["graphify", str(target)]
    if mode:
        cmd += ["--mode", mode]
    subprocess.run(cmd, cwd=str(out_dir), check=True, timeout=timeout)
    return out_dir / "graphify-out" / "graph.json"


def merge(*graphs: NodeLink) -> NodeLink:
    """Merge several NodeLinks into one, de-duplicating nodes by id and edges by triple."""
    nodes: dict[str, dict] = {}
    links: dict[tuple[str, str, str], dict] = {}
    for graph in graphs:
        for node in graph.nodes:
            nodes.setdefault(node["id"], node)
        for link in graph.links:
            links.setdefault((link["source"], link["target"], link.get("rel", "")), link)
    return NodeLink(nodes=list(nodes.values()), links=list(links.values()))
