import pytest

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.evals import (
    build_eval_cases,
    compare_fusion_strategies,
    evaluate_mode,
    evaluate_retrieval,
    render_markdown,
)
from meridian.evals.retrieval import (
    BASELINE_CATEGORY,
    CaseResult,
    EvalCase,
    Metrics,
    NoMatchAnalysis,
    ScoreStats,
    StaleContamination,
    _aggregate,
)
from meridian.indexing import HashingEmbedder, VectorIndex, build_index
from meridian.indexing.store import Hit
from meridian.retrieval import Retriever

# Measured with HashingEmbedder when this suite was written (n=109 matched):
#   mode      Hit@1  Recall@5   MRR
#   vector    0.385    0.624   0.489
#   keyword   0.440    0.688   0.536
#   hybrid    0.394    0.651   0.504
# Floors here are regression guards -- "the pipeline still works and is in
# the right ballpark" -- not quality targets. cascading_failure has no floor
# (it's *expected* to score poorly, see its own test); vocabulary_mismatch
# has a *ceiling*, not a floor (see its own test) -- a real semantic model
# should beat a lexical one there, not the other way around.
MIN_OVERALL_HIT_AT_1 = {"vector": 0.3, "keyword": 0.3, "hybrid": 0.3}
MIN_OVERALL_RECALL_AT_5 = {"vector": 0.5, "keyword": 0.5, "hybrid": 0.5}
MIN_NEAR_DUPLICATE_RECALL_AT_5 = 0.75
MAX_LEXICAL_VOCABULARY_MISMATCH_HIT_AT_1 = 0.15


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def documents(catalog):
    return generate_corpus(catalog)


@pytest.fixture(scope="module")
def retriever(tmp_path_factory, catalog, documents):
    embedder = HashingEmbedder()
    index = VectorIndex(tmp_path_factory.mktemp("chroma"), embedder)
    build_index(documents, catalog, embedder, index)
    return Retriever(index)


@pytest.fixture(scope="module")
def report(retriever, documents):
    return evaluate_retrieval(retriever, documents, embedder_name="hashing-256", modes=["vector", "keyword", "hybrid"])


# --------------------------------------------------------------- eval cases


def test_eval_cases_come_only_from_alerts(documents):
    cases = build_eval_cases(documents)

    assert len(cases) == sum(1 for d in documents if d.doc_type == "alert")
    assert all(c.query for c in cases)


def test_untagged_alerts_get_the_baseline_category(documents):
    cases = {c.incident_id: c for c in build_eval_cases(documents)}
    baseline_alert = next(d for d in documents if d.doc_type == "alert" and d.metadata.get("adversarial_case") is None)

    assert cases[baseline_alert.doc_id].category == BASELINE_CATEGORY


def test_no_match_cases_carry_no_correct_runbook(documents):
    cases = build_eval_cases(documents)

    for case in cases:
        if not case.has_matching_runbook:
            assert case.correct_runbook is None


# ------------------------------------------------------------- aggregation


def _result(rank: int | None) -> CaseResult:
    case = EvalCase("x", "q", "runbook-x", True, BASELINE_CATEGORY)
    hits = [Hit(chunk_id=f"c{i}", text="", score=1.0 - i * 0.1, metadata={"doc_id": f"d{i}"}) for i in range(rank or 0)]
    return CaseResult(case=case, hits=hits, rank=rank)


def test_aggregate_of_all_hits_at_rank_one_is_perfect():
    metrics = _aggregate([_result(1), _result(1)], k=5)

    assert metrics == Metrics(n=2, hit_at_1=1.0, recall_at_k=1.0, mrr=1.0)


def test_aggregate_of_all_misses_is_zero():
    metrics = _aggregate([_result(None), _result(None)], k=5)

    assert metrics == Metrics(n=2, hit_at_1=0.0, recall_at_k=0.0, mrr=0.0)


def test_aggregate_rank_two_counts_for_recall_and_mrr_but_not_hit_at_1():
    metrics = _aggregate([_result(2)], k=5)

    assert metrics.hit_at_1 == 0.0
    assert metrics.recall_at_k == 1.0
    assert metrics.mrr == pytest.approx(0.5)


def test_aggregate_rank_beyond_k_counts_for_mrr_but_not_recall_or_hit_at_1():
    metrics = _aggregate([_result(8)], k=5)

    assert metrics.hit_at_1 == 0.0
    assert metrics.recall_at_k == 0.0
    assert metrics.mrr == pytest.approx(1 / 8)


def test_aggregate_of_no_results_is_all_zero():
    assert _aggregate([], k=5) == Metrics(n=0, hit_at_1=0.0, recall_at_k=0.0, mrr=0.0)


def test_mrr_is_the_mean_reciprocal_rank():
    metrics = _aggregate([_result(1), _result(2), _result(None)], k=5)

    assert metrics.mrr == pytest.approx((1 / 1 + 1 / 2 + 0) / 3)


def test_hit_at_1_is_not_capped_at_one_over_k_unlike_precision_at_k():
    # The whole reason Hit@1 replaced precision@k: with one relevant document
    # per query, "all hits at rank 1" must be able to show a perfect score,
    # not top out at 1/k regardless of how good retrieval is.
    metrics = _aggregate([_result(1)] * 10, k=5)

    assert metrics.hit_at_1 == 1.0


# -------------------------------------------------------- no-match analysis


def test_separable_when_every_unmatched_score_is_below_every_matched_score():
    analysis = NoMatchAnalysis(
        matched=ScoreStats(n=2, mean=0.8, median=0.8, min=0.7, max=0.9),
        unmatched=ScoreStats(n=2, mean=0.5, median=0.5, min=0.4, max=0.6),
    )

    assert analysis.separable is True
    assert analysis.overlap == pytest.approx(0.6 - 0.7)  # negative: real headroom, not just "not overlapping"


def test_not_separable_when_ranges_overlap():
    analysis = NoMatchAnalysis(
        matched=ScoreStats(n=2, mean=0.6, median=0.6, min=0.5, max=0.7),
        unmatched=ScoreStats(n=2, mean=0.55, median=0.55, min=0.4, max=0.6),
    )

    assert analysis.separable is False
    assert analysis.overlap == pytest.approx(0.1)


def test_separability_undefined_without_both_groups():
    analysis = NoMatchAnalysis(matched=None, unmatched=ScoreStats(1, 0.5, 0.5, 0.5, 0.5))

    assert analysis.separable is None
    assert analysis.overlap is None


# ---------------------------------------------------- stale contamination


def test_stale_contamination_rate_from_no_contaminated_cases():
    assert StaleContamination(n_incidents=10, n_contaminated=0, examples=[]).rate == 0.0


def test_stale_contamination_rate_computation():
    assert StaleContamination(n_incidents=4, n_contaminated=1, examples=[("a", "b")]).rate == 0.25


def test_stale_contamination_rate_of_zero_incidents_is_zero_not_a_division_error():
    assert StaleContamination(n_incidents=0, n_contaminated=0, examples=[]).rate == 0.0


def test_stale_contamination_is_measured_against_every_alert_not_just_matched_ones(report, documents):
    total_alerts = sum(1 for d in documents if d.doc_type == "alert")

    for mode_report in report.modes.values():
        assert mode_report.stale_contamination.n_incidents == total_alerts


def test_stale_contamination_examples_reference_real_stale_runbooks(report, documents):
    stale_ids = {d.doc_id for d in documents if d.doc_type == "runbook" and "stale_reference" in d.metadata}

    for mode_report in report.modes.values():
        for incident_id, stale_id in mode_report.stale_contamination.examples:
            assert stale_id in stale_ids


# -------------------------------------------------------------- end to end


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid"])
def test_overall_metrics_meet_the_regression_floor(report, mode):
    assert report.modes[mode].overall.hit_at_1 >= MIN_OVERALL_HIT_AT_1[mode]
    assert report.modes[mode].overall.recall_at_k >= MIN_OVERALL_RECALL_AT_5[mode]


def test_near_duplicate_pairs_are_found_well_above_baseline(report):
    vector = report.modes["vector"]
    near_dup = vector.by_category["near_duplicate_pair"].recall_at_k
    baseline = vector.by_category[BASELINE_CATEGORY].recall_at_k

    assert near_dup >= MIN_NEAR_DUPLICATE_RECALL_AT_5
    assert near_dup > baseline, "the near-duplicate case should be easy to match by design, not merely typical"


def test_vocabulary_mismatch_defeats_a_purely_lexical_retriever(report):
    """This is the regression guard for a real bug: the vocab-mismatch alert
    and its runbook used to share incidental boilerplate ("this") beyond the
    service name, letting keyword search partially solve cases it should have
    no lexical basis for at all. With that fixed, a lexical-only retriever
    (this suite's HashingEmbedder standing in for "vector", plus BM25 for
    "keyword") should score close to zero here -- if it creeps back up,
    something is leaking shared vocabulary into the pair again. The positive
    claim -- that a *real* semantic model succeeds where lexical fails -- is
    proven in test_embeddings.py's real-model tests, since it needs actual
    semantic understanding to demonstrate, which HashingEmbedder cannot do."""
    for mode in ("vector", "keyword"):
        hit_at_1 = report.modes[mode].by_category["vocabulary_mismatch"].hit_at_1
        assert hit_at_1 <= MAX_LEXICAL_VOCABULARY_MISMATCH_HIT_AT_1, f"{mode}: {hit_at_1}"


def test_cascading_failure_is_reported_and_is_the_hardest_category(report):
    """Not a quality floor -- the opposite: this documents that cascade
    alerts (worded around the *affected* services) are genuinely harder to
    match to a root-cause runbook (worded around the *hub* service) than
    every other category, for every mode. A future fix to this should show
    up here as a large jump, not as a broken assertion."""
    vector = report.modes["vector"]
    cascade = vector.by_category["cascading_failure"]

    assert cascade.n == 13
    other_recalls = [m.recall_at_k for cat, m in vector.by_category.items() if cat != "cascading_failure"]
    assert cascade.recall_at_k < min(other_recalls)


def test_every_matched_category_from_the_corpus_is_present_in_every_mode(report):
    expected = {BASELINE_CATEGORY, "near_duplicate_pair", "vocabulary_mismatch", "cascading_failure"}

    for mode_report in report.modes.values():
        assert set(mode_report.by_category) == expected


def test_no_match_incidents_are_excluded_from_hit_recall_mrr(report, documents):
    unmatched_count = sum(1 for d in documents if d.doc_type == "alert" and not d.metadata.get("has_matching_runbook"))
    matched_count = sum(1 for d in documents if d.doc_type == "alert" and d.metadata.get("has_matching_runbook"))

    for mode_report in report.modes.values():
        assert mode_report.overall.n == matched_count
        assert mode_report.no_match.unmatched.n == unmatched_count


def test_no_match_analysis_has_a_score_for_every_unmatched_incident(report, documents):
    unmatched_count = sum(1 for d in documents if d.doc_type == "alert" and not d.metadata.get("has_matching_runbook"))

    assert report.modes["vector"].no_match.unmatched.n == unmatched_count > 0


# -------------------------------------------------------------- fusion comparison


def test_fusion_comparison_covers_every_configured_strategy(retriever, documents):
    comparison = compare_fusion_strategies(retriever, documents)

    assert len(comparison) == 3
    labels = [label for label, _ in comparison]
    assert any("rrf" in label for label in labels)
    assert any("weighted_sum" in label for label in labels)
    for _, metrics in comparison:
        assert metrics.n == 109


def test_evaluate_retrieval_includes_fusion_comparison_only_when_hybrid_is_evaluated(retriever, documents):
    with_hybrid = evaluate_retrieval(retriever, documents, embedder_name="e", modes=["hybrid"])
    without_hybrid = evaluate_retrieval(retriever, documents, embedder_name="e", modes=["vector"])

    assert with_hybrid.fusion_comparison != []
    assert without_hybrid.fusion_comparison == []


# -------------------------------------------------------------------- report


def test_rendered_report_includes_every_mode_and_category(report):
    markdown = render_markdown(report)

    for mode in ("vector", "keyword", "hybrid"):
        assert f"`{mode}`" in markdown
    for label in ("near-duplicate runbook pair", "vocabulary mismatch", "cascading failure", "baseline"):
        assert label in markdown
    assert "No-match / abstention" in markdown
    assert "Weakest category" in markdown
    assert "Stale-runbook contamination" in markdown
    assert "Hybrid fusion" in markdown
    assert "Hit@1" in markdown
    assert "Precision@" not in markdown


def test_report_is_deterministic_apart_from_the_timestamp(retriever, documents):
    a = render_markdown(evaluate_retrieval(retriever, documents, embedder_name="e", modes=["vector"]))
    b = render_markdown(evaluate_retrieval(retriever, documents, embedder_name="e", modes=["vector"]))

    strip_timestamp = lambda s: s.split("\n", 3)[-1]  # drop the "generated ..." line
    assert strip_timestamp(a) == strip_timestamp(b)
