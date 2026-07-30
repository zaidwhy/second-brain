"""Idea-collision engine: pure finder + renderer, plus the one filesystem writer."""

from __future__ import annotations

from second_brain.idea_collisions import (
    CollisionPair,
    find_idea_collisions,
    render_idea_collision_markdown,
    write_idea_collisions,
)
from second_brain.near_dup import EmbeddedNote


def test_empty_notes_returns_empty():
    assert find_idea_collisions([]) == []


def test_single_note_returns_empty():
    assert find_idea_collisions([EmbeddedNote("a", "a.md", [1.0, 0.0])]) == []


def test_orthogonal_different_source_pair_qualifies():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [0.0, 1.0]),
    ]
    pairs = find_idea_collisions(notes, max_similarity=0.25)
    assert [(p.doc_id_a, p.doc_id_b) for p in pairs] == [("a", "b")]
    assert pairs[0].similarity == 0.0


def test_similar_pair_does_not_qualify():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [1.0, 0.01]),  # near-identical, not a collision
    ]
    assert find_idea_collisions(notes, max_similarity=0.25) == []


def test_same_source_pair_excluded_by_default():
    # Orthogonal (would otherwise qualify) but chunked from the same source doc.
    notes = [
        EmbeddedNote("a#0", "same.md", [1.0, 0.0]),
        EmbeddedNote("a#1", "same.md", [0.0, 1.0]),
    ]
    assert find_idea_collisions(notes, max_similarity=0.25) == []


def test_same_source_pair_included_when_flag_disabled():
    notes = [
        EmbeddedNote("a#0", "same.md", [1.0, 0.0]),
        EmbeddedNote("a#1", "same.md", [0.0, 1.0]),
    ]
    pairs = find_idea_collisions(notes, max_similarity=0.25, require_different_source=False)
    assert len(pairs) == 1


def test_boundary_is_inclusive():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [1.0, 1.0]),
    ]
    from second_brain.near_dup import cosine_similarity

    sim = cosine_similarity(notes[0].embedding, notes[1].embedding)
    pairs = find_idea_collisions(notes, max_similarity=sim)
    assert len(pairs) == 1


def test_pairs_sorted_least_related_first():
    notes = [
        EmbeddedNote("a", "a.md", [1.0, 0.0]),
        EmbeddedNote("b", "b.md", [0.9, -0.1]),  # more distant (negative-ish y)
        EmbeddedNote("c", "c.md", [0.0, 1.0]),  # perfectly orthogonal - most unrelated
    ]
    pairs = find_idea_collisions(notes, max_similarity=1.0, top_k=None)
    sims = [p.similarity for p in pairs]
    assert sims == sorted(sims)


def test_top_k_caps_results():
    notes = [EmbeddedNote(f"n{i}", f"n{i}.md", [float(i), float(-i)]) for i in range(5)]
    pairs = find_idea_collisions(notes, max_similarity=1.0, top_k=2)
    assert len(pairs) == 2


def test_no_cap_when_top_k_none():
    notes = [EmbeddedNote(f"n{i}", f"n{i}.md", [float(i), float(-i)]) for i in range(5)]
    pairs = find_idea_collisions(notes, max_similarity=1.0, top_k=None)
    assert len(pairs) == 10  # all 5-choose-2 pairs qualify at max_similarity=1.0


def test_render_includes_both_doc_ids_and_snippets():
    pair = CollisionPair("a", "b", 0.1234)
    notes = {"a": "note about gardening", "b": "note about distributed systems"}
    markdown = render_idea_collision_markdown(pair, notes)
    assert "Idea Collision: a x b" in markdown
    assert "0.1234" in markdown
    assert "note about gardening" in markdown
    assert "note about distributed systems" in markdown
    assert "CANDIDATE PAIRING ONLY" in markdown


def test_render_missing_note_text_shows_placeholder():
    pair = CollisionPair("a", "ghost", 0.0)
    markdown = render_idea_collision_markdown(pair, {"a": "has text"})
    assert "*(no text available)*" in markdown


def test_write_idea_collisions_writes_one_file_per_pair(tmp_path):
    pairs = [CollisionPair("a", "b", 0.1), CollisionPair("c", "d", 0.2)]
    notes = {"a": "alpha", "b": "beta", "c": "gamma", "d": "delta"}
    paths = write_idea_collisions(pairs, notes, tmp_path / "out")
    assert len(paths) == 2
    for path in paths:
        assert path.exists()
        assert path.suffix == ".md"


def test_write_idea_collisions_creates_output_dir(tmp_path):
    out_dir = tmp_path / "nested" / "dir"
    assert not out_dir.exists()
    write_idea_collisions([CollisionPair("a", "b", 0.0)], {"a": "x", "b": "y"}, out_dir)
    assert out_dir.exists()


def test_filenames_are_distinct_for_different_pairs(tmp_path):
    pairs = [CollisionPair("same", "b", 0.1), CollisionPair("same", "c", 0.1)]
    notes = {"same": "x", "b": "y", "c": "z"}
    paths = write_idea_collisions(pairs, notes, tmp_path)
    assert len({p.name for p in paths}) == 2
