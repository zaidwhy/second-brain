"""Auto-linking: document-level aggregation, source exclusion, ranking, and top-k."""

from __future__ import annotations

from dataclasses import dataclass

from second_brain.links import related_notes


@dataclass
class FakeHit:
    doc_id: str
    source: str
    text: str
    rank_score: float


def make_search(hits):
    """Return a search_fn that yields the given hits (ignoring query, honoring k)."""
    return lambda query, k: hits[:k]


def test_excludes_source_document():
    hits = [
        FakeHit("self", "self.md", "text", 0.9),
        FakeHit("other", "other.md", "text", 0.8),
    ]
    results = related_notes(make_search(hits), text="q", source_doc_id="self", k=5)
    assert [r.doc_id for r in results] == ["other"]


def test_aggregates_and_ranks_by_summed_score():
    # "b" wins on two moderate hits over "a" with one strong hit.
    hits = [
        FakeHit("a", "a.md", "strong", 0.7),
        FakeHit("b", "b.md", "one", 0.5),
        FakeHit("b", "b.md", "two", 0.5),
    ]
    results = related_notes(make_search(hits), text="q", k=5)
    assert [r.doc_id for r in results] == ["b", "a"]
    b = results[0]
    assert b.hit_count == 2 and abs(b.score - 1.0) < 1e-9


def test_snippet_uses_best_chunk_and_is_normalized():
    hits = [
        FakeHit("a", "a.md", "weak match", 0.2),
        FakeHit("a", "a.md", "  best   match\n here ", 0.9),
    ]
    results = related_notes(make_search(hits), text="q", k=5)
    assert results[0].snippet == "best match here"


def test_top_k_limit():
    hits = [FakeHit(f"d{i}", f"d{i}.md", "t", 0.9 - i * 0.01) for i in range(10)]
    results = related_notes(make_search(hits), text="q", k=3)
    assert len(results) == 3


def test_empty_hits_returns_empty():
    assert related_notes(make_search([]), text="q", k=5) == []
