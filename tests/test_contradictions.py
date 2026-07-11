"""Contradiction candidate finder: similarity threshold + negation polarity mismatch."""

from __future__ import annotations

from second_brain.contradictions import (
    TextNote,
    find_contradiction_candidates,
    negation_words,
)


def test_negation_words_extracts_known_cues():
    assert negation_words("The gateway is NOT public.") == frozenset({"not"})
    assert negation_words("It isn't reachable from outside.") == frozenset({"isn't"})


def test_negation_words_empty_for_plain_text():
    assert negation_words("The gateway is public.") == frozenset()


def test_finds_candidate_when_similar_and_negation_differs():
    notes = [
        TextNote("a", "a.md", "The gateway is public.", [1.0, 0.0]),
        TextNote("b", "b.md", "The gateway is not public.", [1.0, 0.01]),
    ]
    candidates = find_contradiction_candidates(notes, similarity_threshold=0.99)
    assert [(c.doc_id_a, c.doc_id_b) for c in candidates] == [("a", "b")]
    assert candidates[0].negation_words_b == frozenset({"not"})
    assert candidates[0].negation_words_a == frozenset()


def test_no_candidate_when_both_plain():
    notes = [
        TextNote("a", "a.md", "The gateway is public.", [1.0, 0.0]),
        TextNote("b", "b.md", "The gateway is public today.", [1.0, 0.01]),
    ]
    assert find_contradiction_candidates(notes, similarity_threshold=0.99) == []


def test_no_candidate_when_both_negated():
    notes = [
        TextNote("a", "a.md", "The gateway is not public.", [1.0, 0.0]),
        TextNote("b", "b.md", "The gateway is never public.", [1.0, 0.01]),
    ]
    assert find_contradiction_candidates(notes, similarity_threshold=0.99) == []


def test_no_candidate_when_dissimilar_even_with_negation_mismatch():
    notes = [
        TextNote("a", "a.md", "The gateway is public.", [1.0, 0.0]),
        TextNote("b", "b.md", "The moon is not made of cheese.", [0.0, 1.0]),
    ]
    assert find_contradiction_candidates(notes, similarity_threshold=0.9) == []


def test_boundary_is_inclusive():
    notes = [
        TextNote("a", "a.md", "The gateway is public.", [1.0, 0.0]),
        TextNote("b", "b.md", "The gateway is not public.", [1.0, 1.0]),
    ]
    from second_brain.near_dup import cosine_similarity

    sim = cosine_similarity(notes[0].embedding, notes[1].embedding)
    candidates = find_contradiction_candidates(notes, similarity_threshold=sim)
    assert len(candidates) == 1


def test_sorted_by_similarity_descending():
    notes = [
        TextNote("a", "a.md", "The gateway is public.", [1.0, 0.0]),
        TextNote("b", "b.md", "The gateway is not public.", [1.0, 0.2]),
        TextNote("c", "c.md", "The gateway is not public either.", [1.0, 0.05]),
    ]
    candidates = find_contradiction_candidates(notes, similarity_threshold=0.9)
    sims = [c.similarity for c in candidates]
    assert sims == sorted(sims, reverse=True)


def test_empty_input_returns_empty():
    assert find_contradiction_candidates([]) == []


def test_single_note_returns_empty():
    notes = [TextNote("a", "a.md", "The gateway is public.", [1.0, 0.0])]
    assert find_contradiction_candidates(notes) == []
