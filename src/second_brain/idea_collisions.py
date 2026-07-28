"""Idea-collision engine: pairs topically UNRELATED notes as startup/project idea sparks.

PROJECT-GENESIS.md sec. 1: "generates startup/project ideas from unrelated-note
collisions" (sec. 9 Tier 4 item 29). near_dup.py finds pairs that are too SIMILAR
(candidate duplicates); this module is deliberately the opposite heuristic - it finds
pairs that are dissimilar enough, and from different sources, that combining them could
spark a genuinely new idea (the standard "combinatorial creativity" brainstorming trick:
cross two unrelated domains and see what falls out). Detection only, same contract as
near_dup.py and merge_proposals.py: this never writes the idea text itself (that would
need a model call, out of scope here) - it only ranks and proposes candidate pairs for a
human (or a later LLM step) to riff on.

Two heuristics, both required for a pair to qualify:
1. Low cosine similarity (at or below `max_similarity`) - the notes are NOT about the
   same thing, the mirror image of near_dup's high-similarity bar.
2. Different `source` (unless `require_different_source=False`) - pairing two notes from
   the same source (e.g. the same ingested file, chunked) is a formatting artifact, not a
   cross-domain collision.
Pairs are ranked by similarity ascending (the least related pair first), since maximal
distance is the strongest "these came from completely different worlds" signal.

No personal_llm import: reuses near_dup.cosine_similarity/EmbeddedNote so this stays
testable with fake embeddings and has no vector-store dependency.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from second_brain.near_dup import EmbeddedNote, cosine_similarity

_SNIPPET_LIMIT = 300
_FILENAME_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class CollisionPair:
    doc_id_a: str
    doc_id_b: str
    similarity: float


def find_idea_collisions(
    notes: Sequence[EmbeddedNote],
    *,
    max_similarity: float = 0.25,
    require_different_source: bool = True,
    top_k: int | None = 20,
) -> list[CollisionPair]:
    """All unordered note pairs whose cosine similarity is <= max_similarity (and, unless
    disabled, whose sources differ), least-related first.

    O(n^2) pairwise comparison, same complexity trade-off as
    near_dup.find_near_duplicate_pairs: a "surface a handful of candidates for a human or
    a later LLM step to riff on" tool, not a production ANN index. `top_k` caps the
    result (unrelated pairs are common in any real vault, unlike near-duplicates) - pass
    `None` for no cap.
    """
    pairs: list[CollisionPair] = []
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            a, b = notes[i], notes[j]
            if require_different_source and a.source == b.source:
                continue
            similarity = cosine_similarity(a.embedding, b.embedding)
            if similarity <= max_similarity:
                pairs.append(CollisionPair(a.doc_id, b.doc_id, similarity))
    pairs.sort(key=lambda p: (p.similarity, p.doc_id_a, p.doc_id_b))
    if top_k is not None:
        pairs = pairs[:top_k]
    return pairs


def _snippet(text: str, limit: int = _SNIPPET_LIMIT) -> str:
    """Collapse whitespace and truncate - same idea as merge_proposals.py's snippet."""
    collapsed = " ".join(text.split())
    return collapsed[:limit]


def render_idea_collision_markdown(pair: CollisionPair, notes: Mapping[str, str]) -> str:
    """Deterministic markdown for one collision candidate - no timestamps, no randomness."""
    lines: list[str] = []
    lines.append(f"# Idea Collision: {pair.doc_id_a} x {pair.doc_id_b}")
    lines.append("")
    lines.append(f"**Similarity:** {pair.similarity:.4f} (lower = more unrelated)")
    lines.append("")
    lines.append("## Why these were paired")
    lines.append("")
    lines.append(
        "These notes cleared `second_brain.idea_collisions.find_idea_collisions`'s bar "
        "for being topically UNRELATED (low cosine similarity) and, unless disabled, from "
        "different sources. That is a distance heuristic meant to spark combinatorial "
        "ideas, not a guarantee either note is actually interesting - read both before "
        "acting."
    )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for doc_id in (pair.doc_id_a, pair.doc_id_b):
        lines.append(f"### {doc_id}")
        lines.append("")
        snippet = _snippet(notes.get(doc_id, ""))
        lines.append(snippet if snippet else "*(no text available)*")
        lines.append("")
    lines.append("## Reviewer instructions")
    lines.append("")
    lines.append(
        "This is a CANDIDATE PAIRING ONLY - nothing has been created, merged, or changed. "
        "A human (or a later LLM step) decides whether combining these sparks a genuine "
        "project or startup idea worth writing down."
    )
    lines.append("")
    return "\n".join(lines)


def _pair_filename(pair: CollisionPair) -> str:
    """Deterministic, filesystem-safe filename derived from the pair's doc_ids.

    Sanitizes both doc_ids (which may be full file paths) down to safe characters, then
    appends a short hash of the full pair so two pairs that sanitize to the same prefix
    still get distinct filenames - same approach as merge_proposals.py's filenames.
    """
    safe_a = _FILENAME_UNSAFE_RE.sub("-", pair.doc_id_a).strip("-") or "note"
    safe_b = _FILENAME_UNSAFE_RE.sub("-", pair.doc_id_b).strip("-") or "note"
    digest = hashlib.sha256(f"{pair.doc_id_a}|{pair.doc_id_b}".encode("utf-8")).hexdigest()[:8]
    return f"collision-{safe_a[:40]}-{safe_b[:40]}-{digest}.md"


def write_idea_collisions(
    pairs: Sequence[CollisionPair], notes: Mapping[str, str], output_dir: Path
) -> list[Path]:
    """Write one markdown file per candidate pair to `output_dir`; return the paths written.

    The only effectful function in this module - find_idea_collisions and
    render_idea_collision_markdown are pure, same split as merge_proposals.py.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for pair in pairs:
        path = output_dir / _pair_filename(pair)
        path.write_text(render_idea_collision_markdown(pair, notes), encoding="utf-8")
        paths.append(path)
    return paths
