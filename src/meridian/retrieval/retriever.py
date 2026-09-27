"""The retrieval interface: semantic search with metadata filtering,
configurable k, and a keyword/hybrid path to compare against.

Modes:
- "vector"  -- the Chroma similarity search from meridian.indexing, as-is.
- "keyword" -- BM25 over the same chunks (see keyword.py), for comparison
  against and as one half of hybrid.
- "hybrid"  -- vector and keyword ranked lists combined by Reciprocal Rank
  Fusion. RRF needs no score normalization across the two very different
  scales (cosine similarity vs. BM25), which a weighted-sum blend would.
"""

from __future__ import annotations

from typing import Any, Literal

from meridian.indexing.store import Hit, VectorIndex
from meridian.retrieval.keyword import BM25Index, matches_where, tokenize

Mode = Literal["vector", "keyword", "hybrid"]

# How many candidates each side of a hybrid search contributes before fusion.
# Wider than the final k so fusion has real ranked lists to combine rather
# than two nearly-disjoint top-k's.
FUSION_DEPTH = 20
# Standard RRF damping constant (Cormack et al., 2009) -- large enough that a
# single method's #1 vs #2 doesn't dominate the fused ranking outright.
RRF_K = 60


def _reciprocal_rank_fusion(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


class Retriever:
    def __init__(self, vector_index: VectorIndex) -> None:
        self.vector_index = vector_index
        self._chunks: dict[str, list] | None = None
        self._bm25: BM25Index | None = None
        self._lookup: dict[str, tuple[str, dict[str, Any]]] | None = None

    def _all_chunks(self) -> dict[str, list]:
        if self._chunks is None:
            self._chunks = self.vector_index.all_chunks()
        return self._chunks

    def _keyword_index(self) -> BM25Index:
        if self._bm25 is None:
            chunks = self._all_chunks()
            # Reconstruct the same title+services context the embedder saw
            # (meridian.indexing.chunking.Chunk.embed_text) from metadata,
            # since only the bare chunk text is stored as Chroma's `documents`
            # -- otherwise keyword search would be comparing on less context
            # than vector search, which would bias any vector-vs-keyword
            # comparison before either has run a single query.
            texts = [
                f"{m.get('title', '')} {' '.join(m.get('services', []))} {doc}"
                for doc, m in zip(chunks["documents"], chunks["metadatas"])
            ]
            self._bm25 = BM25Index(chunks["ids"], texts, chunks["metadatas"])
        return self._bm25

    def search(self, query: str, k: int = 5, where: dict[str, Any] | None = None, mode: Mode = "vector") -> list[Hit]:
        if mode == "vector":
            return self.vector_index.query(query, k=k, where=where)
        if mode == "keyword":
            return self._keyword_hits(query, k, where)
        if mode == "hybrid":
            return self._hybrid_hits(query, k, where)
        raise ValueError(f"unknown retrieval mode: {mode!r}")

    def _keyword_hits(self, query: str, k: int, where: dict[str, Any] | None) -> list[Hit]:
        scored = self._keyword_index().search(query, k=k, where=where)
        by_id = self._chunk_lookup()
        return [
            Hit(chunk_id=s.id, text=by_id[s.id][0], score=s.score, metadata=by_id[s.id][1]) for s in scored
        ]

    def _hybrid_hits(self, query: str, k: int, where: dict[str, Any] | None) -> list[Hit]:
        vector_ranking = [h.chunk_id for h in self.vector_index.query(query, k=FUSION_DEPTH, where=where)]
        keyword_ranking = [s.id for s in self._keyword_index().search(query, k=FUSION_DEPTH, where=where)]

        fused = _reciprocal_rank_fusion([vector_ranking, keyword_ranking])
        ranked_ids = sorted(fused, key=lambda item_id: fused[item_id], reverse=True)[:k]

        by_id = self._chunk_lookup()
        return [Hit(chunk_id=cid, text=by_id[cid][0], score=fused[cid], metadata=by_id[cid][1]) for cid in ranked_ids]

    def _chunk_lookup(self) -> dict[str, tuple[str, dict[str, Any]]]:
        if self._lookup is None:
            chunks = self._all_chunks()
            self._lookup = dict(zip(chunks["ids"], zip(chunks["documents"], chunks["metadatas"])))
        return self._lookup


__all__ = ["FUSION_DEPTH", "RRF_K", "Mode", "Retriever", "matches_where", "tokenize"]
