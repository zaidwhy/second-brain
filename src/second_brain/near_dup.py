"""Near-duplicate detector: pure function over note embeddings.

PROJECT-GENESIS sec. 1 wants the graph to "merge duplicate ideas -> merge proposals,
never silent". This module is the detection half only: given each note's embedding, it
finds candidate near-duplicate pairs/clusters by cosine similarity. It never merges,
deletes, or writes anything - a human (or a later merge-proposal generator) decides what
to do with the candidates.

No personal_llm import: callers pass raw (doc_id, source, embedding) triples pulled from
whatever vector store they use, so this stays testable with fake embeddings and has no
vector-store dependency. Plain Python math (no numpy) keeps it dependency-free.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class EmbeddedNote:
    doc_id: str
    source: str
    embedding: Sequence[float]


@dataclass(frozen=True)
class DuplicatePair:
    doc_id_a: str
    doc_id_b: str
    similarity: float


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two vectors; 0.0 for a zero-length (all-zero) vector."""
    if len(a) != len(b):
        raise ValueError(f"embedding length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def find_near_duplicate_pairs(
    notes: Sequence[EmbeddedNote], *, threshold: float = 0.92
) -> list[DuplicatePair]:
    """All unordered note pairs with cosine similarity >= threshold, highest first.

    O(n^2) pairwise comparison - this is a "detect a handful of candidates for human
    review" tool over a vault's notes, not a production ANN index over millions of docs.
    """
    pairs: list[DuplicatePair] = []
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            similarity = cosine_similarity(notes[i].embedding, notes[j].embedding)
            if similarity >= threshold:
                pairs.append(DuplicatePair(notes[i].doc_id, notes[j].doc_id, similarity))
    pairs.sort(key=lambda p: p.similarity, reverse=True)
    return pairs


def cluster_near_duplicates(
    notes: Sequence[EmbeddedNote], *, threshold: float = 0.92
) -> list[list[str]]:
    """Group notes into near-duplicate clusters (union-find over pairwise similarity).

    Clustering is transitive: if A~B and B~C both clear the threshold, all three land in
    one cluster even if A and C alone would not. Singletons (no duplicate found) are
    omitted - callers only want candidates that actually need review. Clusters are
    returned largest-first, each cluster's doc_ids sorted for a deterministic order.
    """
    parent: dict[str, str] = {note.doc_id: note.doc_id for note in notes}

    def find(doc_id: str) -> str:
        while parent[doc_id] != doc_id:
            parent[doc_id] = parent[parent[doc_id]]
            doc_id = parent[doc_id]
        return doc_id

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_a] = root_b

    for pair in find_near_duplicate_pairs(notes, threshold=threshold):
        union(pair.doc_id_a, pair.doc_id_b)

    groups: dict[str, list[str]] = defaultdict(list)
    for note in notes:
        groups[find(note.doc_id)].append(note.doc_id)

    clusters = [sorted(members) for members in groups.values() if len(members) > 1]
    clusters.sort(key=lambda members: (-len(members), members[0]))
    return clusters
