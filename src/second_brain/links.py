"""Auto-linking: given a note, surface the most related *other* notes.

Personal LLM's semantic search returns the most similar *chunks*. Here we aggregate those
chunk hits up to the document level and drop the source note itself, so the result reads as
"notes you should link to" rather than raw fragments. A note that matches on several chunks
ranks above one that matches on a single strong chunk.

No Personal LLM import - the caller injects `search_fn`, so this stays testable with fakes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Protocol


class _Hit(Protocol):
    doc_id: str
    source: str
    text: str
    rank_score: float


# search_fn(query, k) -> list of hits (duck-typed like personal_llm RetrievedChunk).
SearchFn = Callable[[str, int], list]


@dataclass
class RelatedNote:
    doc_id: str
    source: str
    score: float
    snippet: str
    hit_count: int


def related_notes(
    search_fn: SearchFn,
    *,
    text: str,
    source_doc_id: str | None = None,
    k: int = 5,
    search_multiplier: int = 4,
) -> list[RelatedNote]:
    """Notes related to `text`, excluding `source_doc_id`.

    We over-fetch chunks (k * search_multiplier) because several may belong to the same
    document; after aggregating by doc we return the top `k` distinct notes.
    """
    hits = search_fn(text, max(k * search_multiplier, k))
    by_doc: dict[str, list[_Hit]] = defaultdict(list)
    for hit in hits:
        if source_doc_id is not None and hit.doc_id == source_doc_id:
            continue
        by_doc[hit.doc_id].append(hit)

    related: list[RelatedNote] = []
    for doc_id, doc_hits in by_doc.items():
        best = max(doc_hits, key=lambda h: h.rank_score)
        related.append(
            RelatedNote(
                doc_id=doc_id,
                source=best.source,
                score=sum(h.rank_score for h in doc_hits),
                snippet=" ".join(best.text.split())[:200],
                hit_count=len(doc_hits),
            )
        )
    related.sort(key=lambda r: r.score, reverse=True)
    return related[:k]
