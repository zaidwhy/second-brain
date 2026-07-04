"""Knowledge-graph view: turn the Personal LLM knowledge graph into node-link JSON and a
self-contained, offline HTML visualization.

The HTML embeds its data and a tiny vanilla-JS force layout inline - no CDN, no external
fonts or scripts - so it opens straight from disk and honors the local-first ethos.

No Personal LLM import: `to_nodelink` takes duck-typed node/edge objects (personal_llm
KGNode / KGEdge in real use, plain fakes in tests).
"""

from __future__ import annotations

import json
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


@dataclass
class NodeLink:
    nodes: list[dict]
    links: list[dict]

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps({"nodes": self.nodes, "links": self.links}, indent=indent)


def to_nodelink(nodes: Iterable[_Node], edges: Iterable[_Edge]) -> NodeLink:
    """Build a node-link graph, dropping edges that point at a missing node."""
    out_nodes: list[dict] = []
    node_ids: set[str] = set()
    for node in nodes:
        node_ids.add(node.id)
        out_nodes.append({"id": node.id, "name": node.name, "type": node.type})

    out_links: list[dict] = []
    for edge in edges:
        if edge.src in node_ids and edge.dst in node_ids:
            out_links.append({"source": edge.src, "target": edge.dst, "rel": edge.rel})

    return NodeLink(nodes=out_nodes, links=out_links)


def render_html(nodelink: NodeLink, title: str = "Second Brain - Knowledge Graph") -> str:
    """A single self-contained HTML page rendering `nodelink` as a force-directed graph."""
    data = nodelink.to_json(indent=None)
    return _HTML_TEMPLATE.replace("__TITLE__", title).replace("__DATA__", data)


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light dark; }
  html, body { margin: 0; height: 100%; background: #0f1115; color: #e6e6e6;
    font-family: system-ui, sans-serif; }
  #hud { position: fixed; top: 12px; left: 12px; font-size: 13px; opacity: 0.85;
    background: rgba(0,0,0,0.35); padding: 8px 12px; border-radius: 8px; }
  #hud b { font-weight: 600; }
  canvas { display: block; }
</style>
</head>
<body>
<div id="hud"><b>__TITLE__</b><br><span id="stats"></span></div>
<canvas id="c"></canvas>
<script>
const DATA = __DATA__;
const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");
const stats = document.getElementById("stats");

const PALETTE = ["#5b8def","#43b581","#e0a23b","#c265d6","#e06c75","#4db6ac","#b0bec5"];
const typeColor = {};
function colorFor(type) {
  if (!(type in typeColor)) {
    typeColor[type] = PALETTE[Object.keys(typeColor).length % PALETTE.length];
  }
  return typeColor[type];
}

let W = 0, H = 0;
function resize() {
  W = canvas.width = window.innerWidth;
  H = canvas.height = window.innerHeight;
}
window.addEventListener("resize", resize);
resize();

const nodes = DATA.nodes.map(n => Object.assign({}, n, {
  x: W / 2 + (Math.random() - 0.5) * 200,
  y: H / 2 + (Math.random() - 0.5) * 200,
  vx: 0, vy: 0
}));
const index = {};
nodes.forEach(n => index[n.id] = n);
const links = DATA.links
  .map(l => ({ source: index[l.source], target: index[l.target], rel: l.rel }))
  .filter(l => l.source && l.target);

stats.textContent = nodes.length + " nodes, " + links.length + " links";

function step() {
  const REPEL = 4000, SPRING = 0.02, LEN = 90, CENTER = 0.006, DAMP = 0.85;
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    for (let j = i + 1; j < nodes.length; j++) {
      const b = nodes[j];
      let dx = a.x - b.x, dy = a.y - b.y;
      let d2 = dx * dx + dy * dy || 0.01;
      const f = REPEL / d2;
      const d = Math.sqrt(d2);
      const fx = f * dx / d, fy = f * dy / d;
      a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
    }
  }
  for (const l of links) {
    let dx = l.target.x - l.source.x, dy = l.target.y - l.source.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
    const f = SPRING * (d - LEN);
    const fx = f * dx / d, fy = f * dy / d;
    l.source.vx += fx; l.source.vy += fy;
    l.target.vx -= fx; l.target.vy -= fy;
  }
  for (const n of nodes) {
    n.vx += (W / 2 - n.x) * CENTER;
    n.vy += (H / 2 - n.y) * CENTER;
    n.vx *= DAMP; n.vy *= DAMP;
    n.x += n.vx; n.y += n.vy;
  }
}

function draw() {
  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = "rgba(255,255,255,0.15)";
  ctx.lineWidth = 1;
  for (const l of links) {
    ctx.beginPath();
    ctx.moveTo(l.source.x, l.source.y);
    ctx.lineTo(l.target.x, l.target.y);
    ctx.stroke();
  }
  ctx.font = "12px system-ui, sans-serif";
  for (const n of nodes) {
    ctx.beginPath();
    ctx.fillStyle = colorFor(n.type);
    ctx.arc(n.x, n.y, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#e6e6e6";
    ctx.fillText(n.name, n.x + 9, n.y + 4);
  }
}

let ticks = 0;
function frame() {
  if (ticks < 400) { step(); ticks++; }
  draw();
  requestAnimationFrame(frame);
}
frame();

let drag = null;
canvas.addEventListener("mousedown", e => {
  for (const n of nodes) {
    if (Math.hypot(n.x - e.clientX, n.y - e.clientY) < 10) { drag = n; break; }
  }
});
canvas.addEventListener("mousemove", e => {
  if (drag) { drag.x = e.clientX; drag.y = e.clientY; drag.vx = 0; drag.vy = 0; ticks = 0; }
});
window.addEventListener("mouseup", () => drag = null);
</script>
</body>
</html>
"""
