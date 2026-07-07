"""Near-duplicate detector: cosine similarity, pairwise detection, clustering."""

from __future__ import annotations

import math

import pytest

from second_brain.near_dup import (
    EmbeddedNote,
    cluster_near_duplicates,
    cosine_similarity,
    find_near_duplicate_pairs,
)


def test_cosine_similarity_identical_vectors_is_one():
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors_is_minus_one():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_is_zero_not_nan():
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_cosine_similarity_mismatched_length_raises():
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])


def test_find_pairs_above_threshold_only():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [1.0, 0.01]),  # near-identical to a
        EmbeddedNote("c", "c.md", [0.0, 1.0]),  # orthogonal to both
    ]
    pairs = find_near_duplicate_pairs(notes, threshold=0.99)
    assert [(p.doc_id_a, p.doc_id_b) for p in pairs] == [("a", "b")]
    assert pairs[0].similarity > 0.99


def test_find_pairs_sorted_by_similarity_descending():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [1.0, 0.05]),
        EmbeddedNote("c", "c.md", [1.0, 0.2]),
    ]
    pairs = find_near_duplicate_pairs(notes, threshold=0.9)
    sims = [p.similarity for p in pairs]
    assert sims == sorted(sims, reverse=True)


def test_find_pairs_boundary_is_inclusive():
    # Two vectors at exactly a known angle: cos(sim) computed, threshold set to that value.
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [1.0, 1.0]),
    ]
    sim = cosine_similarity(notes[0].embedding, notes[1].embedding)
    pairs = find_near_duplicate_pairs(notes, threshold=sim)
    assert len(pairs) == 1


def test_find_pairs_empty_input_returns_empty():
    assert find_near_duplicate_pairs([]) == []


def test_find_pairs_single_note_returns_empty():
    assert find_near_duplicate_pairs([EmbeddedNote("a", "a.md", [1.0, 0.0])]) == []


def test_cluster_groups_transitively():
    # a~b and b~c both clear the threshold, a~c alone would not - still one cluster.
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0, 0.0]),
        EmbeddedNote("b", "b.md", [0.9, 0.1, 0.0]),
        EmbeddedNote("c", "c.md", [0.75, 0.25, 0.1]),
    ]
    sim_ab = cosine_similarity(notes[0].embedding, notes[1].embedding)
    sim_bc = cosine_similarity(notes[1].embedding, notes[2].embedding)
    sim_ac = cosine_similarity(notes[0].embedding, notes[2].embedding)
    threshold = max(min(sim_ab, sim_bc) - 1e-6, 0)
    assert sim_ac < threshold  # confirms a~c alone would not clear it directly

    clusters = cluster_near_duplicates(notes, threshold=threshold)
    assert clusters == [["a", "b", "c"]]


def test_cluster_omits_singletons():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [1.0, 0.01]),
        EmbeddedNote("lonely", "lonely.md", [0.0, 1.0]),
    ]
    clusters = cluster_near_duplicates(notes, threshold=0.99)
    assert clusters == [["a", "b"]]


def test_cluster_multiple_groups_sorted_largest_first():
    notes = [
        EmbeddedNote("a1", "a1.md", [1.0, 0.0, 0.0]),
        EmbeddedNote("a2", "a2.md", [1.0, 0.001, 0.0]),
        EmbeddedNote("a3", "a3.md", [1.0, 0.002, 0.0]),
        EmbeddedNote("b1", "b1.md", [0.0, 1.0, 0.0]),
        EmbeddedNote("b2", "b2.md", [0.0, 1.0, 0.001]),
    ]
    clusters = cluster_near_duplicates(notes, threshold=0.999)
    assert clusters == [["a1", "a2", "a3"], ["b1", "b2"]]


def test_cluster_empty_input_returns_empty():
    assert cluster_near_duplicates([]) == []


def test_cluster_no_duplicates_returns_empty():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [0.0, 1.0]),
    ]
    assert cluster_near_duplicates(notes, threshold=0.9) == []
