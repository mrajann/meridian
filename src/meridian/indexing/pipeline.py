"""Corpus -> chunks -> embeddings -> index."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from meridian.catalog import ServiceEntry
from meridian.corpus.models import CorpusDocument
from meridian.indexing.chunking import Chunk, chunk_corpus
from meridian.indexing.embeddings import Embedder
from meridian.indexing.store import VectorIndex

# Chunks are sized to 75% of the embedder's input limit: room for the
# contextual header and for a chunker that estimates rather than re-tokenizes
# every candidate, without ever approaching the truncation point.
CHUNK_BUDGET_FRACTION = 0.75


def chunk_budget(embedder: Embedder) -> int:
    return int(embedder.max_input_tokens * CHUNK_BUDGET_FRACTION)


def chunk_metadata(chunk: Chunk, chunk_count: int, catalog: dict[str, ServiceEntry]) -> dict[str, Any]:
    """Metadata a retriever may filter on.

    Built from an explicit allowlist, never by copying the document's own
    metadata: that metadata holds ground-truth labels (correct_runbook,
    root_cause_category, adversarial_case, ...) and letting a retriever
    filter on the answer would make every retrieval eval meaningless.

    `tier` comes from the catalog entry of the document's primary service
    (its first listed service); a service missing from the catalog -- e.g. a
    stale runbook's decommissioned service -- is "unknown".
    """
    primary = chunk.services[0] if chunk.services else None
    entry = catalog.get(primary) if primary else None
    metadata: dict[str, Any] = {
        "doc_id": chunk.doc_id,
        "doc_type": chunk.doc_type,
        "title": chunk.title,
        "chunk_index": chunk.index,
        "chunk_count": chunk_count,
        "tier": str(entry.tier) if entry else "unknown",
    }
    if chunk.services:
        metadata["service"] = primary
        metadata["services"] = list(chunk.services)
    if chunk.section:
        metadata["section"] = chunk.section
    return metadata


@dataclass
class IndexStats:
    documents: int
    chunks: int
    chunks_by_type: dict[str, int]
    max_embed_tokens: int
    chunk_budget: int
    over_budget: list[str] = field(default_factory=list)


def build_index(
    documents: list[CorpusDocument],
    catalog: dict[str, ServiceEntry],
    embedder: Embedder,
    index: VectorIndex,
) -> IndexStats:
    budget = chunk_budget(embedder)
    chunks = chunk_corpus(documents, embedder.count_tokens, budget)

    per_doc = Counter(c.doc_id for c in chunks)
    metadatas = [chunk_metadata(c, per_doc[c.doc_id], catalog) for c in chunks]

    token_counts = {c.chunk_id: embedder.count_tokens(c.embed_text) for c in chunks}
    truncated = [cid for cid, n in token_counts.items() if n > embedder.max_input_tokens]
    if truncated:
        # The chunker sizes to 75% of the limit, so this means an unsplittable
        # oversize word/header -- embedding would silently drop text.
        raise ValueError(f"{len(truncated)} chunks exceed the embedder's input limit, e.g. {truncated[:3]}")

    index.build(chunks, metadatas)

    return IndexStats(
        documents=len(documents),
        chunks=len(chunks),
        chunks_by_type=dict(Counter(c.doc_type for c in chunks)),
        max_embed_tokens=max(token_counts.values(), default=0),
        chunk_budget=budget,
        over_budget=[cid for cid, n in token_counts.items() if n > budget],
    )
