"""Merge-proposal generator: pure builder + renderer, plus the one filesystem writer."""

from __future__ import annotations

from second_brain.merge_proposals import (
    MergeProposal,
    build_merge_proposals,
    render_merge_proposal_markdown,
    write_merge_proposals,
)


def test_empty_cluster_list_returns_empty():
    assert build_merge_proposals([], {}) == []


def test_single_two_note_cluster_has_correct_fields():
    clusters = [["b", "a"]]
    notes = {"a": "short", "b": "a much longer note about the same idea"}
    proposals = build_merge_proposals(clusters, notes)
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.doc_ids == ("a", "b")
    assert proposal.primary_doc_id == "b"  # longer text wins
    assert proposal.snippets["a"] == "short"
    assert proposal.snippets["b"] == "a much longer note about the same idea"


def test_primary_tie_break_prefers_longest_text():
    clusters = [["x", "y"]]
    notes = {"x": "aaaa", "y": "b"}
    proposals = build_merge_proposals(clusters, notes)
    assert proposals[0].primary_doc_id == "x"


def test_primary_tie_break_falls_back_to_lexicographic_id_on_equal_length():
    clusters = [["zeta", "alpha", "beta"]]
    notes = {"zeta": "same", "alpha": "same", "beta": "same"}
    proposals = build_merge_proposals(clusters, notes)
    assert proposals[0].primary_doc_id == "alpha"


def test_primary_tie_break_is_deterministic_regardless_of_cluster_order():
    notes = {"zeta": "same", "alpha": "same", "beta": "same"}
    forward = build_merge_proposals([["alpha", "beta", "zeta"]], notes)
    backward = build_merge_proposals([["zeta", "beta", "alpha"]], notes)
    assert forward[0].primary_doc_id == backward[0].primary_doc_id == "alpha"


def test_missing_note_text_gets_empty_snippet_not_a_crash():
    clusters = [["a", "ghost"]]
    notes = {"a": "has text"}
    proposals = build_merge_proposals(clusters, notes)
    assert proposals[0].snippets["ghost"] == ""
    # ghost has empty (shortest) text, so "a" is primary.
    assert proposals[0].primary_doc_id == "a"


def test_multiple_clusters_produce_multiple_proposals():
    clusters = [["a", "b"], ["c", "d", "e"]]
    notes = {k: f"note {k}" for k in "abcde"}
    proposals = build_merge_proposals(clusters, notes)
    assert len(proposals) == 2
    assert proposals[0].doc_ids == ("a", "b")
    assert proposals[1].doc_ids == ("c", "d", "e")


def test_render_is_deterministic():
    proposal = MergeProposal(
        doc_ids=("a", "b"),
        primary_doc_id="a",
        snippets={"a": "note a text", "b": "note b text"},
    )
    first = render_merge_proposal_markdown(proposal)
    second = render_merge_proposal_markdown(proposal)
    assert first == second


def test_render_contains_every_doc_id():
    proposal = MergeProposal(
        doc_ids=("note-1", "note-2", "note-3"),
        primary_doc_id="note-2",
        snippets={"note-1": "x", "note-2": "y", "note-3": "z"},
    )
    rendered = render_merge_proposal_markdown(proposal)
    for doc_id in proposal.doc_ids:
        assert doc_id in rendered


def test_render_marks_the_primary_and_states_proposal_only():
    proposal = MergeProposal(
        doc_ids=("a", "b"),
        primary_doc_id="a",
        snippets={"a": "text a", "b": "text b"},
    )
    rendered = render_merge_proposal_markdown(proposal)
    assert "a (proposed primary)" in rendered
    assert "b (proposed primary)" not in rendered
    assert "PROPOSAL ONLY" in rendered
    assert "Nothing has been merged or deleted" in rendered


def test_render_cites_near_dup_as_the_source_of_the_grouping():
    proposal = MergeProposal(doc_ids=("a", "b"), primary_doc_id="a", snippets={"a": "x", "b": "y"})
    rendered = render_merge_proposal_markdown(proposal)
    assert "near_dup" in rendered
    assert "cluster_near_duplicates" in rendered


def test_write_writes_one_file_per_cluster(tmp_path):
    clusters = [["a", "b"], ["c", "d"]]
    notes = {"a": "text a", "b": "text b", "c": "text c", "d": "text d"}
    proposals = build_merge_proposals(clusters, notes)

    paths = write_merge_proposals(proposals, tmp_path)

    assert len(paths) == 2
    for path, proposal in zip(paths, proposals):
        assert path.exists()
        assert path.read_text(encoding="utf-8") == render_merge_proposal_markdown(proposal)


def test_write_creates_the_output_dir_if_missing(tmp_path):
    out_dir = tmp_path / "nested" / "merge-proposals"
    proposals = build_merge_proposals([["a", "b"]], {"a": "text a", "b": "text b"})

    paths = write_merge_proposals(proposals, out_dir)

    assert out_dir.is_dir()
    assert len(paths) == 1
    assert paths[0].parent == out_dir


def test_write_empty_proposals_writes_nothing(tmp_path):
    assert write_merge_proposals([], tmp_path) == []


def test_write_filenames_are_deterministic_across_runs(tmp_path):
    proposals = build_merge_proposals([["a", "b"]], {"a": "text a", "b": "text b"})
    first = write_merge_proposals(proposals, tmp_path / "run1")
    second = write_merge_proposals(proposals, tmp_path / "run2")
    assert first[0].name == second[0].name
