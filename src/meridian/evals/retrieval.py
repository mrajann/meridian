"""Retrieval evaluation: Hit@1, recall@5, MRR against the corpus's own
alerts, which already carry ground truth (correct_runbook, has_matching_runbook,
adversarial_case) from how the corpus is generated -- no separate labelled
eval set needs to be authored for this.

Every alert in the corpus has exactly one relevant runbook (or none). A
precision@k built on a single relevant document is capped at 1/k no matter
how good retrieval is (one hit out of k slots), which makes it look like
every mode is failing when the real ceiling is the metric, not the
retriever -- so the top-of-ranking metric here is Hit@1 (did the correct
runbook come back first) instead. Recall@k and MRR still use the full
ranked list. Alerts without a matching runbook (has_matching_runbook=False)
have no positive to score against and are excluded from these metrics --
they get their own no-match/abstention analysis instead (see NoMatchAnalysis
below), which is the actually meaningful question for them.
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


def _evaluate_case(retriever: Retriever, case: EvalCase, mode: Mode, search_depth: int, **search_kwargs) -> CaseResult:
    hits = _dedupe_by_doc(
        retriever.search(case.query, k=search_depth, where=build_filter(doc_type="runbook"), mode=mode, **search_kwargs)
    )
    rank = next((i for i, h in enumerate(hits, start=1) if h.doc_id == case.correct_runbook), None)
    return CaseResult(case=case, hits=hits, rank=rank)


@dataclass(frozen=True)
class Metrics:
    n: int
    hit_at_1: float
    recall_at_k: float
    mrr: float


def _aggregate(results: list[CaseResult], k: int) -> Metrics:
    if not results:
        return Metrics(n=0, hit_at_1=0.0, recall_at_k=0.0, mrr=0.0)

    # Exactly one relevant document per case, so "found within k" is both
    # recall@k (relevant/1) and what MRR's numerator needs.
    hits_at_1 = [r.rank == 1 for r in results]
    hits_at_k = [r.rank is not None and r.rank <= k for r in results]
    reciprocal_ranks = [1.0 / r.rank if r.rank is not None else 0.0 for r in results]

    return Metrics(
        n=len(results),
        hit_at_1=sum(hits_at_1) / len(results),
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
class StaleContamination:
    """Stale runbooks (referencing a decommissioned service) have no alert of
    their own -- nothing should ever consider one the *correct* answer -- so
    the meaningful question isn't precision/recall, it's whether they leak
    into results for real incidents anyway: does a stale runbook turn up in
    the top k for a query it has no business matching?

    stale_reference is looked up from the source CorpusDocument metadata, not
    the index: ground-truth-adjacent fields are deliberately never indexed
    (see meridian.indexing.pipeline.chunk_metadata), so this is an
    eval-time-only cross-reference, not something retrieval could filter on.
    """

    n_incidents: int
    n_contaminated: int
    examples: list[tuple[str, str]]  # (incident_id, stale runbook doc_id), first few

    @property
    def rate(self) -> float:
        return self.n_contaminated / self.n_incidents if self.n_incidents else 0.0


@dataclass(frozen=True)
class ModeReport:
    mode: Mode
    k: int
    overall: Metrics
    by_category: dict[str, Metrics]
    no_match: NoMatchAnalysis
    stale_contamination: StaleContamination
    case_results: list[CaseResult]


# Fusion configurations compared in every generated report, so the answer to
# "how is hybrid weighted, and is that the best choice" stays current instead
# of living only in a code comment that can drift from what's actually
# configured. (label, fusion algorithm, vector_weight, keyword_weight).
FUSION_COMPARISON_CONFIGS: list[tuple[str, str, float, float]] = [
    ("rrf, 1:1 (unweighted)", "rrf", 1.0, 1.0),
    ("weighted_sum, 1:1", "weighted_sum", 1.0, 1.0),
    ("weighted_sum, 3:1 (current default)", "weighted_sum", 3.0, 1.0),
]


def compare_fusion_strategies(
    retriever: Retriever,
    documents: list[CorpusDocument],
    k: int = DEFAULT_K,
    search_depth: int = SEARCH_DEPTH,
    configs: list[tuple[str, str, float, float]] = FUSION_COMPARISON_CONFIGS,
) -> list[tuple[str, Metrics]]:
    """Overall (matched-incidents) metrics for each hybrid fusion config, run
    against the current index -- what backs the "how is hybrid weighted"
    question with real, current numbers rather than a value fixed when this
    was last tuned by hand."""
    cases = [c for c in build_eval_cases(documents) if c.has_matching_runbook]
    comparison = []
    for label, fusion, vector_weight, keyword_weight in configs:
        results = [
            _evaluate_case(
                retriever, case, "hybrid", search_depth,
                fusion=fusion, vector_weight=vector_weight, keyword_weight=keyword_weight,
            )
            for case in cases
        ]
        comparison.append((label, _aggregate(results, k)))
    return comparison


@dataclass(frozen=True)
class RetrievalEvalReport:
    embedder_name: str
    modes: dict[Mode, ModeReport]
    fusion_comparison: list[tuple[str, Metrics]]
    generated_at: str


def _stale_contamination(results: list[CaseResult], stale_ids: set[str], k: int) -> StaleContamination:
    examples = []
    n_contaminated = 0
    for r in results:
        hit = next((h for h in r.hits[:k] if h.doc_id in stale_ids), None)
        if hit is not None:
            n_contaminated += 1
            if len(examples) < 5:
                examples.append((r.case.incident_id, hit.doc_id))
    return StaleContamination(n_incidents=len(results), n_contaminated=n_contaminated, examples=examples)


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

    stale_ids = {doc.doc_id for doc in documents if doc.doc_type == "runbook" and "stale_reference" in doc.metadata}

    return ModeReport(
        mode=mode,
        k=k,
        overall=_aggregate(matched, k),
        by_category=by_category,
        no_match=no_match,
        stale_contamination=_stale_contamination(results, stale_ids, k),
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
        fusion_comparison=compare_fusion_strategies(retriever, documents, k) if "hybrid" in modes else [],
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
