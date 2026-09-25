"""Retrieval evaluation: precision@k, recall@k, MRR against the corpus's own
alerts, which already carry ground truth (correct_runbook, has_matching_runbook,
adversarial_case) from how the corpus is generated -- no separate labelled
eval set needs to be authored for this.

Every alert in the corpus has exactly one relevant runbook (or none), so
precision@k/recall@k/MRR reduce to: is the correct runbook's chunk among the
top k (deduplicated to one entry per document), and at what rank. Alerts
without a matching runbook (has_matching_runbook=False) have no positive to
score against and are excluded from these metrics -- they get their own
no-match/abstention analysis instead (see NoMatchAnalysis below), which is
the actually meaningful question for them.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from meridian.corpus.models import CorpusDocument
from meridian.indexing.store import Hit, build_filter
from meridian.retrieval import Mode, Retriever

DEFAULT_K = 5
# Retrieved depth per query; deeper than k so MRR can find a correct runbook
# ranked just outside the top k instead of always reporting 0 for it.
SEARCH_DEPTH = 10

BASELINE_CATEGORY = "baseline"  # alerts with no adversarial_case tag


@dataclass(frozen=True)
class EvalCase:
    incident_id: str
    query: str
    correct_runbook: str | None
    has_matching_runbook: bool
    category: str  # adversarial_case, or BASELINE_CATEGORY


def build_eval_cases(documents: list[CorpusDocument]) -> list[EvalCase]:
    return [
        EvalCase(
            incident_id=doc.doc_id,
            query=doc.body,
            correct_runbook=doc.metadata.get("correct_runbook"),
            has_matching_runbook=bool(doc.metadata.get("has_matching_runbook")),
            category=doc.metadata.get("adversarial_case") or BASELINE_CATEGORY,
        )
        for doc in documents
        if doc.doc_type == "alert"
    ]


def _dedupe_by_doc(hits: list[Hit]) -> list[Hit]:
    """First (highest-ranked) chunk per doc_id, rank order preserved -- a
    document should count once no matter how many of its chunks appear."""
    seen: set[str] = set()
    deduped = []
    for hit in hits:
        if hit.doc_id not in seen:
            seen.add(hit.doc_id)
            deduped.append(hit)
    return deduped


@dataclass(frozen=True)
class CaseResult:
    case: EvalCase
    hits: list[Hit]  # deduped by doc_id, rank order
    rank: int | None  # 1-based rank of the correct runbook, or None if not found within SEARCH_DEPTH

    @property
    def top_score(self) -> float | None:
        return self.hits[0].score if self.hits else None


def _evaluate_case(retriever: Retriever, case: EvalCase, mode: Mode, search_depth: int) -> CaseResult:
    hits = _dedupe_by_doc(
        retriever.search(case.query, k=search_depth, where=build_filter(doc_type="runbook"), mode=mode)
    )
    rank = next((i for i, h in enumerate(hits, start=1) if h.doc_id == case.correct_runbook), None)
    return CaseResult(case=case, hits=hits, rank=rank)


@dataclass(frozen=True)
class Metrics:
    n: int
    precision_at_k: float
    recall_at_k: float
    mrr: float


def _aggregate(results: list[CaseResult], k: int) -> Metrics:
    if not results:
        return Metrics(n=0, precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)

    # Exactly one relevant document per case, so hit/k is precision@k and
    # hit/1 is recall@k -- the single-relevant-document form of both metrics.
    hits_at_k = [r.rank is not None and r.rank <= k for r in results]
    reciprocal_ranks = [1.0 / r.rank if r.rank is not None else 0.0 for r in results]

    return Metrics(
        n=len(results),
        precision_at_k=sum(hits_at_k) / len(results) / k,
        recall_at_k=sum(hits_at_k) / len(results),
        mrr=statistics.mean(reciprocal_ranks),
    )


@dataclass(frozen=True)
class ScoreStats:
    n: int
    mean: float
    median: float
    min: float
    max: float


def _score_stats(scores: list[float]) -> ScoreStats | None:
    if not scores:
        return None
    return ScoreStats(
        n=len(scores), mean=statistics.mean(scores), median=statistics.median(scores),
        min=min(scores), max=max(scores),
    )


@dataclass(frozen=True)
class NoMatchAnalysis:
    """Whether the top-1 similarity score alone could tell an agent 'abstain,
    I have no real match' apart from 'yes, this is the answer'."""

    matched: ScoreStats | None
    unmatched: ScoreStats | None

    @property
    def separable(self) -> bool | None:
        """True if every unmatched top score is below every matched top score
        -- i.e. a single threshold would perfectly separate them. None if
        either group is empty."""
        if not self.matched or not self.unmatched:
            return None
        return self.unmatched.max < self.matched.min

    @property
    def overlap(self) -> float | None:
        """How much the two score ranges overlap, in score units. 0 (or
        negative headroom below) means cleanly separable; positive means a
        band of scores that both matched and unmatched cases land in, where a
        threshold alone can't decide."""
        if not self.matched or not self.unmatched:
            return None
        return self.unmatched.max - self.matched.min


@dataclass(frozen=True)
class ModeReport:
    mode: Mode
    k: int
    overall: Metrics
    by_category: dict[str, Metrics]
    no_match: NoMatchAnalysis
    case_results: list[CaseResult]


@dataclass(frozen=True)
class RetrievalEvalReport:
    embedder_name: str
    modes: dict[Mode, ModeReport]
    generated_at: str


def evaluate_mode(
    retriever: Retriever,
    documents: list[CorpusDocument],
    mode: Mode,
    k: int = DEFAULT_K,
    search_depth: int = SEARCH_DEPTH,
) -> ModeReport:
    cases = build_eval_cases(documents)
    results = [_evaluate_case(retriever, case, mode, search_depth) for case in cases]

    matched = [r for r in results if r.case.has_matching_runbook]
    unmatched = [r for r in results if not r.case.has_matching_runbook]

    by_category: dict[str, Metrics] = {}
    for category in sorted({r.case.category for r in matched}):
        by_category[category] = _aggregate([r for r in matched if r.case.category == category], k)

    no_match = NoMatchAnalysis(
        matched=_score_stats([r.top_score for r in matched if r.top_score is not None]),
        unmatched=_score_stats([r.top_score for r in unmatched if r.top_score is not None]),
    )

    return ModeReport(
        mode=mode,
        k=k,
        overall=_aggregate(matched, k),
        by_category=by_category,
        no_match=no_match,
        case_results=results,
    )


def evaluate_retrieval(
    retriever: Retriever,
    documents: list[CorpusDocument],
    embedder_name: str,
    modes: list[Mode] = ("vector", "keyword", "hybrid"),
    k: int = DEFAULT_K,
) -> RetrievalEvalReport:
    from datetime import datetime, timezone

    return RetrievalEvalReport(
        embedder_name=embedder_name,
        modes={mode: evaluate_mode(retriever, documents, mode, k) for mode in modes},
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
