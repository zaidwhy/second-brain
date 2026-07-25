"""Merge-proposal generator: near-duplicate clusters -> human-reviewable proposal docs.

PROJECT-GENESIS sec. 9 Tier 4 item 28. near_dup.py detects near-duplicate note clusters
but, by design, never merges anything (PROJECT-GENESIS sec. 1: "merges duplicate ideas ->
merge proposals, never silent"). This module is the missing other half: it turns a
cluster of doc_ids into a markdown document a human can read and act on. It never edits,
merges, or deletes a note - it only writes a new proposal file that says "these look like
duplicates, here is each one's content, you decide."

Primary-selection tie-break rule: within a cluster, the member with the longest text is
proposed as the canonical/primary doc_id (ties broken by the lexicographically-first
doc_id). Longest text is a cheap, dependency-free proxy for "most complete version" - the
note least likely to be missing content the others have. It is only a suggestion for the
reviewer's convenience (rendered as "(proposed primary)"); nothing is actually kept or
discarded automatically. The lexicographic tie-break makes the choice deterministic (and
therefore testable byte-for-byte) when two members have identical length.

No personal_llm import: `build_merge_proposals` takes near_dup.cluster_near_duplicates's
exact `list[list[str]]` return shape plus a plain `dict[str, str]` of doc_id -> note text,
so this stays testable with fake data and has no vector-store or CLI dependency. Only
`write_merge_proposals` touches the filesystem - everything upstream of it is pure.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

_SNIPPET_LIMIT = 300
_FILENAME_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class MergeProposal:
    doc_ids: tuple[str, ...]
    primary_doc_id: str
    snippets: dict[str, str]


def _snippet(text: str, limit: int = _SNIPPET_LIMIT) -> str:
    """Collapse whitespace and truncate - same idea as links.py's related-note snippet."""
    collapsed = " ".join(text.split())
    return collapsed[:limit]


def _pick_primary(doc_ids: Sequence[str], notes: Mapping[str, str]) -> str:
    """Longest text wins; ties (including missing/empty text) broken by doc_id, ascending."""
    return min(doc_ids, key=lambda doc_id: (-len(notes.get(doc_id, "")), doc_id))


def build_merge_proposals(
    clusters: Sequence[Sequence[str]], notes: Mapping[str, str]
) -> list[MergeProposal]:
    """One MergeProposal per cluster. Clusters and notes are never mutated.

    `notes` maps doc_id -> full note text; a doc_id present in a cluster but missing from
    `notes` gets an empty snippet rather than raising - a reviewer should still see the
    cluster even if one member's text could not be looked up.
    """
    proposals: list[MergeProposal] = []
    for cluster in clusters:
        doc_ids = tuple(sorted(cluster))
        if not doc_ids:
            continue
        primary = _pick_primary(doc_ids, notes)
        snippets = {doc_id: _snippet(notes.get(doc_id, "")) for doc_id in doc_ids}
        proposals.append(MergeProposal(doc_ids=doc_ids, primary_doc_id=primary, snippets=snippets))
    return proposals


def render_merge_proposal_markdown(proposal: MergeProposal) -> str:
    """Deterministic markdown for one proposal - no timestamps, no random ordering."""
    lines: list[str] = []
    lines.append(f"# Merge Proposal: {proposal.primary_doc_id}")
    lines.append("")
    lines.append(f"**Notes flagged ({len(proposal.doc_ids)}):** " + ", ".join(proposal.doc_ids))
    lines.append("")
    lines.append("## Why these were flagged")
    lines.append("")
    lines.append(
        "These notes were grouped into one near-duplicate cluster by "
        "`second_brain.near_dup.cluster_near_duplicates` (cosine similarity over their "
        "embeddings cleared the configured threshold, transitively). That is a similarity "
        "heuristic, not a guarantee the notes say the same thing - review the content below "
        "before acting."
    )
    lines.append("")
    lines.append("## Members")
    lines.append("")
    for doc_id in proposal.doc_ids:
        marker = " (proposed primary)" if doc_id == proposal.primary_doc_id else ""
        lines.append(f"### {doc_id}{marker}")
        lines.append("")
        snippet = proposal.snippets.get(doc_id, "")
        lines.append(snippet if snippet else "*(no text available)*")
        lines.append("")
    lines.append("## Reviewer instructions")
    lines.append("")
    lines.append(
        "This is a PROPOSAL ONLY. Nothing has been merged or deleted - all notes above still "
        "exist unchanged. A human must review the content, decide whether these are actually "
        "duplicates, and if so choose how to combine or remove them."
    )
    lines.append("")
    return "\n".join(lines)


def _proposal_filename(proposal: MergeProposal) -> str:
    """Deterministic, filesystem-safe filename derived from the proposal's contents.

    Sanitizes the primary doc_id (which may be a full file path) down to safe characters,
    then appends a short hash of the full doc_id set so two proposals whose primary ids
    sanitize to the same string still get distinct filenames.
    """
    safe = _FILENAME_UNSAFE_RE.sub("-", proposal.primary_doc_id).strip("-") or "note"
    digest = hashlib.sha256("|".join(proposal.doc_ids).encode("utf-8")).hexdigest()[:8]
    return f"merge-{safe[:60]}-{digest}.md"


def write_merge_proposals(proposals: Sequence[MergeProposal], output_dir: Path) -> list[Path]:
    """Write one markdown file per proposal to `output_dir`; return the paths written.

    The only effectful function in this module - everything upstream (build_merge_proposals,
    render_merge_proposal_markdown) is pure and unit-testable with tmp_path, same split as
    cli.py's `graph` command writing render_html's output to settings.graph_html_path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for proposal in proposals:
        path = output_dir / _proposal_filename(proposal)
        path.write_text(render_merge_proposal_markdown(proposal), encoding="utf-8")
        paths.append(path)
    return paths
