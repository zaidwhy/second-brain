"""Contradiction candidate finder: similarity + negation-cue heuristic.

PROJECT-GENESIS sec. 9 Tier 2: a companion to near_dup.py's duplicate detector. Where
near_dup flags notes saying the *same* thing twice, this flags notes that are topically
similar (same embedding neighborhood) but disagree on negation polarity - "the API is
public" next to "the API is not public". It is a heuristic filter for human review, not
a logical proof of contradiction: same "detect candidates, never merge/decide" contract
as near_dup.py.

No personal_llm import: callers pass raw (doc_id, source, text, embedding) tuples, so
this stays testable with fake embeddings and has no vector-store dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from second_brain.near_dup import cosine_similarity

NEGATION_CUES = frozenset(
    {
        "not",
        "no",
        "never",
        "none",
        "nobody",
        "nothing",
        "neither",
        "nor",
        "cannot",
        "can't",
        "won't",
        "don't",
        "doesn't",
        "didn't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
        "haven't",
        "hasn't",
        "hadn't",
        "shouldn't",
        "wouldn't",
        "couldn't",
    }
)

_WORD_RE = re.compile(r"[a-z']+")


@dataclass(frozen=True)
class TextNote:
    doc_id: str
    source: str
    text: str
    embedding: Sequence[float]


@dataclass(frozen=True)
class ContradictionCandidate:
    doc_id_a: str
    doc_id_b: str
    similarity: float
    negation_words_a: frozenset[str]
    negation_words_b: frozenset[str]


def negation_words(text: str) -> frozenset[str]:
    """Negation-cue tokens present in `text` (lowercased, punctuation-stripped)."""
    tokens = _WORD_RE.findall(text.lower())
    return frozenset(t for t in tokens if t in NEGATION_CUES)


def find_contradiction_candidates(
    notes: Sequence[TextNote], *, similarity_threshold: float = 0.75
) -> list[ContradictionCandidate]:
    """Note pairs that are topically similar but disagree on negation polarity.

    Two notes about the same thing (embedding cosine similarity >= threshold) where
    exactly one contains a negation cue and the other doesn't are candidates for a
    real contradiction, worth a human's attention. O(n^2) pairwise comparison, same
    "handful of candidates for review" scale as near_dup.find_near_duplicate_pairs.
    """
    candidates: list[ContradictionCandidate] = []
    for i in range(len(notes)):
        for j in range(i + 1, len(notes)):
            a, b = notes[i], notes[j]
            similarity = cosine_similarity(a.embedding, b.embedding)
            if similarity < similarity_threshold:
                continue
            neg_a = negation_words(a.text)
            neg_b = negation_words(b.text)
            if bool(neg_a) == bool(neg_b):
                continue
            candidates.append(
                ContradictionCandidate(a.doc_id, b.doc_id, similarity, neg_a, neg_b)
            )
    candidates.sort(key=lambda c: c.similarity, reverse=True)
    return candidates
