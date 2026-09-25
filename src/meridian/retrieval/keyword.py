"""Pure-Python Okapi BM25 keyword search over the same chunks that are in the
vector index, plus a matcher for the `where` clauses meridian.indexing.store
produces, so vector and keyword search accept identical filters.

Built from `VectorIndex.all_chunks()` rather than by re-chunking the corpus,
so the keyword index can never drift out of sync with what the vector index
actually holds.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

_WORD_RE = re.compile(r"[a-z0-9]+")

# BM25 constants (Robertson-Sparck Jones defaults).
_K1 = 1.5
_B = 0.75


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def matches_where(metadata: dict[str, Any], where: dict[str, Any] | None) -> bool:
    """Evaluates the subset of Chroma's `where` language that
    meridian.indexing.store.build_filter() actually produces: equality,
    $in, $contains (on a list-valued field), and $and of those."""
    if where is None:
        return True
    if "$and" in where:
        return all(matches_where(metadata, clause) for clause in where["$and"])

    (key, condition), = where.items()
    value = metadata.get(key)
    if isinstance(condition, dict):
        if "$in" in condition:
            return value in condition["$in"]
        if "$contains" in condition:
            return condition["$contains"] in (value or [])
        raise ValueError(f"unsupported where operator: {condition}")
    return value == condition


@dataclass(frozen=True)
class ScoredId:
    id: str
    score: float


class BM25Index:
    def __init__(self, ids: list[str], texts: list[str], metadatas: list[dict[str, Any]]) -> None:
        self._ids = ids
        self._metadatas = metadatas
        self._doc_tokens = [tokenize(t) for t in texts]
        self._doc_len = [len(toks) for toks in self._doc_tokens]
        self._avg_len = (sum(self._doc_len) / len(self._doc_len)) if self._doc_len else 0.0

        doc_freq: Counter[str] = Counter()
        for toks in self._doc_tokens:
            doc_freq.update(set(toks))
        n = len(ids)
        # BM25's standard idf; floored at a small positive value so a term in
        # every document still contributes a little rather than going negative.
        self._idf = {
            term: max(math.log((n - df + 0.5) / (df + 0.5) + 1.0), 1e-9) for term, df in doc_freq.items()
        }

    def search(self, query: str, k: int, where: dict[str, Any] | None = None) -> list[ScoredId]:
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scores: list[tuple[int, float]] = []
        for i, metadata in enumerate(self._metadatas):
            if not matches_where(metadata, where):
                continue
            term_counts = Counter(self._doc_tokens[i])
            length_norm = _K1 * (1 - _B + _B * self._doc_len[i] / self._avg_len) if self._avg_len else _K1
            score = 0.0
            for term in query_terms:
                freq = term_counts.get(term, 0)
                if freq == 0:
                    continue
                idf = self._idf.get(term, 0.0)
                score += idf * (freq * (_K1 + 1)) / (freq + length_norm)
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda pair: pair[1], reverse=True)
        return [ScoredId(id=self._ids[i], score=score) for i, score in scores[:k]]
