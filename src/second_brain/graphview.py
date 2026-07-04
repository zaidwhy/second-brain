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
  :root {
    --ink: #10141b;
    --ink-2: #161c26;
    --text: #e9e4d6;
    --muted: #8b93a1;
    --accent: #e8b768;
    --edge: rgba(198, 210, 230, 0.10);
    --panel: rgba(16, 20, 27, 0.72);
    --hairline: rgba(233, 228, 214, 0.12);
    --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
    --mono: ui-monospace, "Cascadia Code", "SF Mono", Consolas, monospace;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; overflow: hidden; }
  body {
    background:
      radial-gradient(120% 90% at 78% 6%, #1b2433 0%, rgba(27, 36, 51, 0) 55%),
      radial-gradient(120% 120% at 12% 100%, #171a14 0%, rgba(23, 26, 20, 0) 50%),
      var(--ink);
    color: var(--text);
    font-family: var(--sans);
  }
  canvas { display: block; position: fixed; inset: 0; }

  .hud { position: fixed; top: 22px; left: 24px; z-index: 3; pointer-events: none; }
  .title {
    font-family: var(--serif);
    font-weight: 500;
    font-size: clamp(20px, 3.4vw, 34px);
    letter-spacing: 0.01em;
    margin: 0;
    text-shadow: 0 1px 20px rgba(0, 0, 0, 0.55);
  }
  .stats {
    font-family: var(--mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
    margin-top: 8px;
  }

  .legend {
    position: fixed; bottom: 22px; left: 24px; z-index: 3;
    display: flex; flex-wrap: wrap; gap: 6px 16px; max-width: 46vw;
  }
  .legend .chip {
    display: flex; align-items: center; gap: 8px;
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.06em;
    color: var(--muted);
  }
  .legend .dot { width: 9px; height: 9px; border-radius: 50%; flex: none; }

  .hint {
    position: fixed; bottom: 22px; right: 24px; z-index: 3;
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em;
    color: var(--muted); text-align: right; pointer-events: none;
  }

  .readout {
    position: fixed; top: 22px; right: 24px; z-index: 4;
    width: min(300px, 68vw); padding: 16px 18px;
    background: var(--panel); border: 1px solid var(--hairline);
    border-radius: 12px; backdrop-filter: blur(9px);
    opacity: 0; transform: translateY(-6px); transition: opacity 0.16s ease, transform 0.16s ease;
  }
  .readout.on { opacity: 1; transform: none; }
  .readout .name { font-family: var(--serif); font-size: 19px; line-height: 1.2; }
  .readout .kind {
    font-family: var(--mono); font-size: 11px; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--accent); margin-top: 4px;
  }
  .readout .rels { margin-top: 12px; display: grid; gap: 7px; }
  .readout .rel { font-size: 13px; color: var(--text); display: flex; gap: 8px; align-items: baseline; }
  .readout .rel .verb { font-family: var(--mono); font-size: 11px; color: var(--muted); flex: none; }
  .readout .empty { font-size: 13px; color: var(--muted); margin-top: 10px; }

  .void {
    position: fixed; inset: 0; z-index: 2; display: none;
    flex-direction: column; align-items: center; justify-content: center;
    text-align: center; padding: 24px;
  }
  .void.on { display: flex; }
  .void h2 { font-family: var(--serif); font-weight: 500; font-size: clamp(24px, 4vw, 40px); margin: 0 0 12px; }
  .void p { max-width: 42ch; color: var(--muted); line-height: 1.6; margin: 0; }
  .void code { font-family: var(--mono); color: var(--text); }

  @media (max-width: 620px) {
    .legend { max-width: 90vw; }
    .hint { display: none; }
  }
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="hud">
  <h1 class="title">__TITLE__</h1>
  <div class="stats" id="stats"></div>
</div>
<div class="legend" id="legend"></div>
<div class="hint">hover to trace connections<br>drag to arrange</div>
<aside class="readout" id="readout" aria-live="polite"></aside>
<div class="void" id="void">
  <h2>Nothing mapped yet</h2>
  <p>Ingest a vault and run with a triple-capable model, then export again. Your notes will
  grow into a graph of the ideas that connect them.</p>
</div>
<script>
const DATA = __DATA__;
const PALETTE = ["#58b4c9", "#e0a15a", "#a88be0", "#e07a9a", "#8bc06a", "#6a9de0"];
const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const types = [...new Set(DATA.nodes.map(n => n.type))].sort();
const colorFor = t => PALETTE[Math.max(0, types.indexOf(t)) % PALETTE.length];

document.getElementById("stats").textContent =
  DATA.nodes.length + " nodes \\u00b7 " + DATA.links.length + " links";

if (DATA.nodes.length === 0) {
  document.getElementById("void").classList.add("on");
  document.getElementById("legend").style.display = "none";
  document.querySelector(".hint").style.display = "none";
} else {
  const counts = {};
  DATA.nodes.forEach(n => counts[n.type] = (counts[n.type] || 0) + 1);
  document.getElementById("legend").innerHTML = types.map(t =>
    '<span class="chip"><span class="dot" style="background:' + colorFor(t) + '"></span>' +
    t + " (" + counts[t] + ")</span>").join("");
  runGraph();
}

function runGraph() {
  let W, H, dpr = Math.min(window.devicePixelRatio || 1, 2);
  function resize() {
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener("resize", resize); resize();

  const index = {};
  const nodes = DATA.nodes.map(n => {
    const o = Object.assign({ deg: 0 }, n,
      { x: W / 2 + (Math.random() - 0.5) * 260, y: H / 2 + (Math.random() - 0.5) * 260, vx: 0, vy: 0 });
    index[n.id] = o; return o;
  });
  const neighbors = {};
  nodes.forEach(n => neighbors[n.id] = new Set());
  const links = DATA.links.map(l => ({ s: index[l.source], t: index[l.target], rel: l.rel }))
    .filter(l => l.s && l.t && l.s !== l.t);
  links.forEach(l => {
    l.s.deg++; l.t.deg++;
    neighbors[l.s.id].add(l.t.id); neighbors[l.t.id].add(l.s.id);
  });
  const radius = n => 5 + Math.min(9, Math.sqrt(n.deg) * 2.4);

  let focus = null;
  let dragging = null;
  const showAllLabels = nodes.length <= 40;

  function step() {
    const REPEL = 5200, SPRING = 0.022, LEN = 96, CENTER = 0.005, DAMP = 0.86;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy || 0.01;
        const d = Math.sqrt(d2), f = REPEL / d2;
        const fx = f * dx / d, fy = f * dy / d;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }
    }
    for (const l of links) {
      let dx = l.t.x - l.s.x, dy = l.t.y - l.s.y, d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = SPRING * (d - LEN), fx = f * dx / d, fy = f * dy / d;
      l.s.vx += fx; l.s.vy += fy; l.t.vx -= fx; l.t.vy -= fy;
    }
    for (const n of nodes) {
      n.vx += (W / 2 - n.x) * CENTER; n.vy += (H / 2 - n.y) * CENTER;
      n.vx *= DAMP; n.vy *= DAMP;
      if (n !== dragging) { n.x += n.vx; n.y += n.vy; }
    }
  }

  function dim(id) {
    if (!focus) return 1;
    if (id === focus.id) return 1;
    return neighbors[focus.id].has(id) ? 0.95 : 0.14;
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    for (const l of links) {
      const active = focus && (l.s.id === focus.id || l.t.id === focus.id);
      ctx.strokeStyle = active ? "rgba(232, 183, 104, 0.55)" : "rgba(198, 210, 230, 0.10)";
      ctx.lineWidth = active ? 1.6 : 1;
      ctx.beginPath(); ctx.moveTo(l.s.x, l.s.y); ctx.lineTo(l.t.x, l.t.y); ctx.stroke();
    }
    ctx.font = "12px system-ui, sans-serif";
    for (const n of nodes) {
      const a = dim(n.id), r = radius(n);
      ctx.globalAlpha = a;
      ctx.beginPath(); ctx.fillStyle = colorFor(n.type); ctx.arc(n.x, n.y, r, 0, Math.PI * 2); ctx.fill();
      if (focus && n.id === focus.id) {
        ctx.lineWidth = 2; ctx.strokeStyle = "#e8b768"; ctx.stroke();
      }
      const label = showAllLabels || (focus && a > 0.5);
      if (label) {
        ctx.fillStyle = "rgba(0,0,0,0.55)"; ctx.fillText(n.name, n.x + r + 6 + 0.6, n.y + 4 + 0.6);
        ctx.fillStyle = "#e9e4d6"; ctx.fillText(n.name, n.x + r + 6, n.y + 4);
      }
      ctx.globalAlpha = 1;
    }
  }

  let ticks = 0, settle = reduce ? 500 : 420;
  if (reduce) { for (let i = 0; i < settle; i++) step(); }
  function frame() {
    if (!reduce && ticks < settle) { step(); ticks++; }
    draw();
    requestAnimationFrame(frame);
  }
  frame();

  const readout = document.getElementById("readout");
  function nodeAt(mx, my) {
    for (const n of nodes) { if (Math.hypot(n.x - mx, n.y - my) < radius(n) + 5) return n; }
    return null;
  }
  function setFocus(n) {
    focus = n;
    if (!n) { readout.classList.remove("on"); return; }
    const rels = links.filter(l => l.s.id === n.id || l.t.id === n.id).map(l => {
      const out = l.s.id === n.id;
      return { verb: (out ? "" : "") + (l.rel || "linked"), other: (out ? l.t : l.s).name, out };
    });
    readout.innerHTML =
      '<div class="name">' + esc(n.name) + '</div><div class="kind">' + esc(n.type) + '</div>' +
      (rels.length
        ? '<div class="rels">' + rels.map(r =>
            '<div class="rel"><span class="verb">' + (r.out ? "&#8594; " : "&#8592; ") + esc(r.verb) +
            '</span><span>' + esc(r.other) + '</span></div>').join("") + '</div>'
        : '<div class="empty">No links from this node yet.</div>');
    readout.classList.add("on");
  }
  function esc(s) { return String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

  canvas.addEventListener("mousemove", e => {
    if (dragging) { dragging.x = e.clientX; dragging.y = e.clientY; dragging.vx = dragging.vy = 0; ticks = 0; return; }
    const n = nodeAt(e.clientX, e.clientY);
    canvas.style.cursor = n ? "pointer" : "default";
    setFocus(n);
  });
  canvas.addEventListener("mousedown", e => { const n = nodeAt(e.clientX, e.clientY); if (n) dragging = n; });
  window.addEventListener("mouseup", () => dragging = null);
  canvas.addEventListener("mouseleave", () => { if (!dragging) setFocus(null); });
}
</script>
</body>
</html>
"""
