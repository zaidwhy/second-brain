# Knowledge-graph viewer - UI design language

Documents the UI as it actually exists in `src/second_brain/graphview.py`
(`render_html`), the only UI this repo ships. There is no other screen, no
CLI TUI, no web app - `ingest_vault` and friends are library calls exposed
through `interfaces/cli.py`, and the graph viewer is the one place a human
looks at pixels. This file describes what is there today; it does not
propose new UI.

Companion doc: `docs/ADAPTERS.md` covers the ingestion-adapter interface,
not the viewer.

## What it is

`render_html(nodelink, title=...)` returns one self-contained HTML string:
a `<!doctype html>` document with inline `<style>` and inline `<script>`,
no `<link>`, no external `<script src>`, no web fonts, no CDN. The data
(`nodelink.to_json()`) is embedded directly into the script as a JS object
literal (`const DATA = __DATA__;`), with `</` escaped to `<\/` so a node or
edge value can never terminate the inline `<script>` tag early
(`graphview.py` lines 57-60; regression-tested by
`test_render_html_script_safe_names`). This is why the module docstring
and `CLAUDE.md` insist it must "stay fully self-contained" - the file is
meant to be opened straight from disk (`file://...`) with no server and no
network, matching the local-first ethos of the whole `personal-llm`
ecosystem.

`graphify_adapter.py` does not add any UI of its own. It only produces
`NodeLink` objects (via `parse_graphify_json`) from an external tool's
`graph.json`, so a Graphify code-graph can be merged (`merge()`) with the
notes graph and rendered through the exact same `render_html`.

## DOM structure

```
<canvas id="c">                 - the graph itself; the only thing that
                                   actually draws nodes/edges
<div class="hud">                - top-left: title + node/link count
  <h1 class="title">
  <div class="stats" id="stats">
<div class="legend" id="legend"> - bottom-left: one chip per node type,
                                    populated by JS, hidden if empty graph
<div class="hint">               - bottom-right: static usage hint text
<aside class="readout" id="readout"> - top-right: focused-node detail
                                        panel, hidden until hover
<div class="void" id="void">     - full-screen empty-state message,
                                    shown only when there are zero nodes
```

Everything except `<canvas>` is positioned `fixed` and stacked with
`z-index` (canvas has none / implicit 0, `.void` is 2, HUD/legend/hint are
3, the readout panel is 4 so it sits above everything). `html, body` are
`overflow: hidden` at `height: 100%` - the page is a single fixed viewport,
never scrolls.

## Typography

Three font stacks, each named as a CSS custom property and used for a
fixed purpose - never mixed within one element:

- `--serif` (`"Iowan Old Style", "Palatino Linotype", Palatino, Georgia,
  serif`) - the two big display moments: the page `.title` and the
  `.readout .name` / `.void h2` headings. Nothing else uses it.
- `--sans` (`system-ui, -apple-system, "Segoe UI", sans-serif`) - the
  `<body>` default. In practice almost nothing renders in it directly,
  since the HUD/legend/hint/readout all set their own font-family; it is
  the fallback for `.readout .rel` body text and `.void p`.
- `--mono` (`ui-monospace, "Cascadia Code", "SF Mono", Consolas,
  monospace`) - every small uppercase/tracked label: `.stats`, `.legend
  .chip`, `.hint`, `.readout .kind`, `.readout .rel .verb`.

Sizes are small and mostly fixed px (11-13px for mono labels, 19px for
the readout name), except the two serif headings, which use `clamp()` so
they scale with viewport width: `.title` is `clamp(20px, 3.4vw, 34px)`,
`.void h2` is `clamp(24px, 4vw, 40px)`.

Canvas text (node labels) does not use any of these three variables at
all - CSS custom properties are invisible to a 2D canvas context. Node
labels are drawn with a hardcoded `"12px system-ui, sans-serif"`
(`graphview.py` line 272), a second, independent copy of the `--sans`
stack's first two names typed out again because canvas has no access to
the `<style>` block.

## Color system

Defined once as CSS custom properties on `:root`:

| token | value | used for |
|---|---|---|
| `--ink` | `#10141b` | page background base color |
| `--ink-2` | `#161c26` | declared, **not referenced anywhere** (dead) |
| `--text` | `#e9e4d6` | primary text color, canvas label fill |
| `--muted` | `#8b93a1` | secondary/label text (stats, legend, hint, kind labels' sibling text) |
| `--accent` | `#e8b768` | `.readout .kind` text color; also the focus/highlight color inside the canvas (see below) |
| `--edge` | `rgba(198, 210, 230, 0.10)` | declared, **not referenced anywhere in CSS** (dead) |
| `--panel` | `rgba(16, 20, 27, 0.72)` | `.readout` background |
| `--hairline` | `rgba(233, 228, 214, 0.12)` | `.readout` border |

The body background is two radial gradients (a cool blue-grey top-right,
a warm dark-olive bottom-left) layered over `var(--ink)` - a fixed vignette,
not theme-able and not affected by node data.

Node/edge colors in the canvas are a **second, separate palette** that CSS
custom properties cannot reach (canvas draw calls take literal color
strings, not `var(...)`):

- `PALETTE` (line 180): six hardcoded hex colors
  (`#58b4c9, #e0a15a, #a88be0, #e07a9a, #8bc06a, #6a9de0`) assigned to node
  *types* in sorted order via `colorFor(type)`, cycling with `% PALETTE.length`
  if there are more than six distinct types. This is what fills both the
  legend dots and the node circles - the one part of the design that is
  literally data-driven (depends on how many distinct `type` values are in
  the graph).
- Edge (link) lines are not type-colored: inactive edges are
  `rgba(198, 210, 230, 0.10)` and edges touching the hovered node switch to
  an accent-colored `rgba(232, 183, 104, 0.55)` at 1.6px instead of 1px.
- The focused node's ring stroke is `#e8b768` at 2px.

`rgba(232, 183, 104, 0.55)` and `#e8b768` are the same RGB triple
(232, 183, 104 = 0xE8, 0xB7, 0x68) written two different ways in two
different places in the script, and neither one is derived from the
`--accent` custom property that already holds that exact value in CSS -
canvas can't consume a CSS variable, so the color was simply retyped by
hand at both call sites. That is the one real, fixable duplication this
pass addresses (see "Polish fix" below): it is not a visual bug today
(both copies agree), but it is a latent one - a future edit to the accent
hue would have to be made in three places (CSS `--accent`, the ring
stroke, and the active-edge rgba) and nothing would flag it if one were
missed.

## Layout and spacing

Everything is `position: fixed`, positioned from the four corners of the
viewport with the same `22px`/`24px` offsets (`.hud`/`.legend`/`.hint` at
`22px` from top or bottom and `24px` from left or right, `.readout` at
`22px`/`24px` from top-right). Interior spacing runs on an 4-8px rhythm:
`gap: 6px 16px` in `.legend`, `gap: 8px` in `.readout .rel`, `gap: 7px` in
`.readout .rels`, `padding: 16px 18px` in `.readout`. Corner rounding is
`border-radius: 12px` on the readout panel and `50%` (a circle) on legend
dots. There is one explicit breakpoint, `@media (max-width: 620px)`, which
shrinks the legend's max-width to `90vw` and hides `.hint` entirely (a
mouse-only affordance that doesn't apply on the narrow/touch case anyway).

## Node and edge rendering rules

All of this lives in the `runGraph()` function, which only runs when
`DATA.nodes.length > 0` (otherwise the `.void` empty state is shown and
`runGraph()` is never called):

- **Node radius**: `radius(n) = 5 + min(9, sqrt(deg) * 2.4)` - a degree-0
  node draws at 5px, and radius grows with the square root of how many
  edges touch the node, capped at 14px total. `nodeAt()` hit-testing uses
  `radius(n) + 5` as the hover/click tolerance, so small nodes still have
  a comfortably larger click target than their visible circle.
- **Node color**: `colorFor(n.type)`, from `PALETTE` above.
- **Node label**: drawn only when `showAllLabels` (true if there are 40 or
  fewer nodes total) or when a node is within the focused node's
  neighborhood (`dim(n.id) > 0.5`) - so a large graph stays legible by
  only labeling what's relevant to the current hover, while a small graph
  just labels everything all the time. Labels are drawn twice per node - a
  `rgba(0,0,0,0.55)` shadow copy offset by `(0.6, 0.6)` px, then the real
  `--text`-colored (`#e9e4d6`, hardcoded) copy on top - a cheap manual
  text-shadow, since canvas has no CSS `text-shadow`.
- **Edge styling**: see the color table above - plain 1px muted-blue lines
  by default, thickened and accent-colored only for edges touching the
  currently-focused node.
- **Dimming**: `dim(id)` returns `1` when nothing is focused or the id is
  the focus itself, `0.95` for the focus's direct neighbors, and `0.14`
  for everything else - so hovering a node fades the rest of the graph
  without fully hiding it, applied to both node fill alpha and (via the
  label-visibility check) label rendering.

## Interaction behavior

There is no pan and no zoom anywhere in the viewer - the canvas is a fixed
one-to-one view of the simulated layout; the only ways to change what you
see are hovering and dragging:

- **Hover** (`mousemove` with nothing held down): `nodeAt()` finds the
  nearest node under the cursor within its hit radius, `setFocus()` is
  called, the cursor becomes a pointer over a node, and the `.readout`
  panel fades/slides in (`opacity`/`transform` transition, 0.16s) showing
  the node's name, type, and every relationship it participates in
  (arrow direction shows whether the node is the edge's source or
  target). Moving off every node (or `mouseleave` while not dragging)
  calls `setFocus(null)`, which fades the readout back out.
- **Drag** (`mousedown` on a node, then `mousemove`, released on
  `mouseup`): pins that node's position to the cursor and zeroes its
  velocity every frame while held, restarting the force-layout settle
  countdown (`ticks = 0`) so the rest of the graph relaxes around the new
  position. There is no click-to-pin-permanently or click-to-select
  gesture distinct from hover/drag - a plain click with no movement is
  just a zero-distance drag.
- **No keyboard interaction** - the graph is mouse-only. Nothing in the
  markup takes focus or has a `tabindex`, so this view is not currently
  keyboard-navigable (the `.readout aria-live="polite"` attribute means a
  screen reader will announce its text content when it changes, but a
  screen-reader or keyboard-only user has no way to trigger that change).
- **`prefers-reduced-motion: reduce`**: the force simulation still runs
  (nodes must end up somewhere), but instead of animating settle over ~420
  `requestAnimationFrame` ticks it runs 500 layout steps synchronously
  before the first paint, so a reduced-motion user sees one static,
  already-settled layout instead of nodes visibly drifting into place.
  Hover/drag interaction still works identically afterward.

## Empty-state

If `nodelink.nodes` is empty, `runGraph()` never runs at all: the `.void`
panel ("Nothing mapped yet" / ingest-a-vault copy) is shown, and the
legend and hint are explicitly hidden via inline `style.display = "none"`
rather than a CSS rule, since they're otherwise always-visible elements.

## Known inconsistencies found while writing this doc

Documented for completeness; only the first is fixed in this pass (see
below) because it is the only one that is a pure literal-duplication
consolidation with zero behavior or visual change. The other two are
pre-existing dead CSS and are left alone - removing "unused" custom
properties is a different, slightly riskier kind of change (it assumes
nothing outside this file's own `<style>` block ever reads them, which is
true today but is a different claim than "same value, zero visual
change") and is out of scope for this pass.

1. **Accent color duplicated three ways** - `--accent: #e8b768` (CSS), and
   the same RGB triple retyped by hand as `"#e8b768"` and
   `"rgba(232, 183, 104, 0.55)"` inside the canvas script, because canvas
   drawing can't read a CSS custom property. Fixed in this pass (below).
2. **`--ink-2: #161c26`** is declared on `:root` and never used by any
   rule in the stylesheet.
3. **`--edge: rgba(198, 210, 230, 0.10)`** is declared on `:root` and
   never used via `var(--edge)` anywhere - the identical value is instead
   hardcoded directly as the inactive-edge canvas stroke color, for the
   same reason as (1): canvas can't consume the CSS variable.

## Polish fix in this pass

Added one JS constant, `ACCENT_RGB = "232, 183, 104"` (commented as
matching CSS `--accent: #e8b768`), and pointed both existing canvas call
sites at it instead of retyping the triple: the focus-ring stroke is now
`"rgb(" + ACCENT_RGB + ")"` and the active-edge stroke is now
`"rgba(" + ACCENT_RGB + ", 0.55)"`. `rgb(232, 183, 104)` and `#e8b768` are
the same color, and the rgba string is byte-identical to before - this is
a pure single-sourcing of one already-consistent literal, not a visual
change. See `tests/test_graphview.py::test_accent_rgb_is_single_sourced`.
