"""The retrieval interface: semantic search with metadata filtering,
configurable k, and a keyword/hybrid path to compare against.

Modes:
- "vector"  -- the Chroma similarity search from meridian.indexing, as-is.
- "keyword" -- BM25 over the same chunks (see keyword.py), for comparison
  against and as one half of hybrid.
- "hybrid"  -- vector and keyword combined. Two fusion algorithms are
  available (see `fusion`); both are weighted, because keyword is
  consistently the weaker retriever here (see reports/retrieval_eval.md),
  and an unweighted 1:1 blend drags a strong vector ranking down by mixing
  in a weaker one rather than only picking up genuinely complementary hits.
"""

from __future__ import annotations

from typing import Any, Literal

from meridian.indexing.store import Hit, VectorIndex
from meridian.retrieval.keyword import BM25Index, ScoredId, matches_where, tokenize

Mode = Literal["vector", "keyword", "hybrid"]
Fusion = Literal["rrf", "weighted_sum"]

# How many candidates each side of a hybrid search contributes before fusion.
# Wider than the final k so fusion has real ranked lists to combine rather
# than two nearly-disjoint top-k's.
FUSION_DEPTH = 20
# Standard RRF damping constant (Cormack et al., 2009) -- large enough that a
# single method's #1 vs #2 doesn't dominate the fused ranking outright.
RRF_K = 60

# Default fusion algorithm and weights. See reports/retrieval_eval.md
# ("Hybrid fusion") for current, regenerated-on-every-run numbers rather than
# a snapshot here that can drift out of sync with what's actually measured --
# as of the investigation that set these defaults: unweighted 1:1 RRF (the
# original default) underperformed pure vector on Hit@1/recall/MRR, because
# RRF only sees rank, not how confident either side is, so with RRF_K's
# damping, reweighting it barely moved the fused order at all. weighted_sum
# normalizes each side's raw scores to [0, 1] over its own candidate pool
# first, so a confident #1 actually outweighs a weak one; at 3:1 it beat pure
# vector outright (not merely approximated it) by still picking up keyword's
# genuinely complementary wins (BM25 clearly wins on near-duplicate pairs,
# where the deciding signal is a literal named entity, not a paraphrase)
# while vector's already-good ranking dominates the rest.
DEFAULT_VECTOR_WEIGHT = 3.0
DEFAULT_KEYWORD_WEIGHT = 1.0
DEFAULT_FUSION: Fusion = "weighted_sum"


def _reciprocal_rank_fusion(weighted_rankings: list[tuple[list[str], float]], k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking, weight in weighted_rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + weight / (k + rank)
    return scores


def _minmax_normalize(scored: list[ScoredId]) -> dict[str, float]:
    if not scored:
        return {}
    values = [s.score for s in scored]
    lo, hi = min(values), max(values)
    if hi == lo:
        return {s.id: 1.0 for s in scored}
    return {s.id: (s.score - lo) / (hi - lo) for s in scored}


def _weighted_sum_fusion(
    vector_hits: list[Hit], keyword_hits: list[ScoredId], vector_weight: float, keyword_weight: float
) -> dict[str, float]:
    """Alternative to RRF: min-max normalize each side's raw scores to [0, 1]
    over its own candidate pool, then combine linearly. Unlike RRF (which
    only sees rank), this lets a method express *how much* better its #1 is
    than its #2 -- at the cost of that normalization being pool-dependent
    rather than a stable, comparable unit like RRF's rank-based score."""
    vector_norm = _minmax_normalize([ScoredId(h.chunk_id, h.score) for h in vector_hits])
    keyword_norm = _minmax_normalize(keyword_hits)

    scores: dict[str, float] = {}
    for item_id, value in vector_norm.items():
        scores[item_id] = scores.get(item_id, 0.0) + vector_weight * value
    for item_id, value in keyword_norm.items():
        scores[item_id] = scores.get(item_id, 0.0) + keyword_weight * value
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

    def search(
        self,
        query: str,
        k: int = 5,
        where: dict[str, Any] | None = None,
        mode: Mode = "vector",
        fusion: Fusion = DEFAULT_FUSION,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
    ) -> list[Hit]:
        if mode == "vector":
            return self.vector_index.query(query, k=k, where=where)
        if mode == "keyword":
            return self._keyword_hits(query, k, where)
        if mode == "hybrid":
            return self._hybrid_hits(query, k, where, fusion, vector_weight, keyword_weight)
        raise ValueError(f"unknown retrieval mode: {mode!r}")

    def _keyword_hits(self, query: str, k: int, where: dict[str, Any] | None) -> list[Hit]:
        scored = self._keyword_index().search(query, k=k, where=where)
        by_id = self._chunk_lookup()
        return [
            Hit(chunk_id=s.id, text=by_id[s.id][0], score=s.score, metadata=by_id[s.id][1]) for s in scored
        ]

    def _hybrid_hits(
        self,
        query: str,
        k: int,
        where: dict[str, Any] | None,
        fusion: Fusion,
        vector_weight: float,
        keyword_weight: float,
    ) -> list[Hit]:
        vector_hits = self.vector_index.query(query, k=FUSION_DEPTH, where=where)
        keyword_scored = self._keyword_index().search(query, k=FUSION_DEPTH, where=where)

        if fusion == "rrf":
            fused = _reciprocal_rank_fusion(
                [
                    ([h.chunk_id for h in vector_hits], vector_weight),
                    ([s.id for s in keyword_scored], keyword_weight),
                ]
            )
        elif fusion == "weighted_sum":
            fused = _weighted_sum_fusion(vector_hits, keyword_scored, vector_weight, keyword_weight)
        else:
            raise ValueError(f"unknown fusion algorithm: {fusion!r}")

        ranked_ids = sorted(fused, key=lambda item_id: fused[item_id], reverse=True)[:k]

        by_id = self._chunk_lookup()
        return [Hit(chunk_id=cid, text=by_id[cid][0], score=fused[cid], metadata=by_id[cid][1]) for cid in ranked_ids]

    def _chunk_lookup(self) -> dict[str, tuple[str, dict[str, Any]]]:
        if self._lookup is None:
            chunks = self._all_chunks()
            self._lookup = dict(zip(chunks["ids"], zip(chunks["documents"], chunks["metadatas"])))
        return self._lookup


__all__ = [
    "DEFAULT_FUSION",
    "DEFAULT_KEYWORD_WEIGHT",
    "DEFAULT_VECTOR_WEIGHT",
    "FUSION_DEPTH",
    "RRF_K",
    "Fusion",
    "Mode",
    "Retriever",
    "matches_where",
    "tokenize",
]
