import pytest

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.evals import (
    analyze_abstention,
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
    ScoreStats,
    SignalAnalysis,
    StaleContamination,
    ThresholdResult,
    _aggregate,
    _auc,
    _best_threshold,
    _score_stats,
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


# ---------------------------------------------------- abstention statistics


def test_score_stats_includes_sample_standard_deviation():
    stats = _score_stats([1.0, 2.0, 3.0, 4.0])

    assert stats == ScoreStats(n=4, mean=2.5, std=pytest.approx(1.2909944), median=2.5, min=1.0, max=4.0)


def test_score_stats_of_a_single_value_has_zero_std_not_an_error():
    assert _score_stats([0.5]).std == 0.0


def test_score_stats_of_nothing_is_none():
    assert _score_stats([]) is None


def test_auc_is_one_when_every_matched_score_beats_every_unmatched_score():
    assert _auc([0.7, 0.8], [0.1, 0.2]) == 1.0


def test_auc_is_zero_when_every_unmatched_score_beats_every_matched_score():
    assert _auc([0.1, 0.2], [0.7, 0.8]) == 0.0


def test_auc_counts_ties_as_half():
    assert _auc([0.5], [0.5]) == 0.5


def test_auc_is_a_coin_flip_for_identical_distributions():
    assert _auc([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.5


def test_auc_without_both_groups_is_undefined():
    assert _auc([], [0.5]) is None
    assert _auc([0.5], []) is None


def test_best_threshold_on_perfectly_separable_scores_gets_everything_right():
    best = _best_threshold(matched=[0.7, 0.8, 0.9], unmatched=[0.1, 0.2, 0.3])

    assert best.abstain_correctly == 1.0
    assert best.abstain_wrongly == 0.0
    assert best.balanced_accuracy == 1.0
    assert 0.3 < best.threshold <= 0.7


def test_best_threshold_on_overlapping_scores_reports_the_tradeoff():
    # One unmatched value (0.6) sits above one matched value (0.5): no
    # threshold gets both groups fully right.
    best = _best_threshold(matched=[0.5, 0.7, 0.8], unmatched=[0.2, 0.3, 0.6])

    assert best.balanced_accuracy < 1.0
    assert best.balanced_accuracy == pytest.approx(
        (best.abstain_correctly + (1 - best.abstain_wrongly)) / 2
    )


def test_best_threshold_rule_is_answer_at_or_above_and_abstain_below():
    best = _best_threshold(matched=[0.6], unmatched=[0.4])

    assert best == ThresholdResult(threshold=0.6, abstain_correctly=1.0, abstain_wrongly=0.0, balanced_accuracy=1.0)


def test_signal_separable_when_every_unmatched_value_is_below_every_matched_value():
    signal = SignalAnalysis(
        name="x",
        matched=ScoreStats(n=2, mean=0.8, std=0.1, median=0.8, min=0.7, max=0.9),
        unmatched=ScoreStats(n=2, mean=0.5, std=0.1, median=0.5, min=0.4, max=0.6),
        auc=1.0,
        best_threshold=None,
    )

    assert signal.separable is True
    assert signal.overlap == pytest.approx(0.6 - 0.7)  # negative: real headroom, not just "no overlap"


def test_signal_not_separable_when_ranges_overlap():
    signal = SignalAnalysis(
        name="x",
        matched=ScoreStats(n=2, mean=0.6, std=0.1, median=0.6, min=0.5, max=0.7),
        unmatched=ScoreStats(n=2, mean=0.55, std=0.1, median=0.55, min=0.4, max=0.6),
        auc=0.6,
        best_threshold=None,
    )

    assert signal.separable is False
    assert signal.overlap == pytest.approx(0.1)


def test_signal_separability_undefined_without_both_groups():
    signal = SignalAnalysis(
        name="x", matched=None, unmatched=ScoreStats(1, 0.5, 0.0, 0.5, 0.5, 0.5), auc=None, best_threshold=None
    )

    assert signal.separable is None
    assert signal.overlap is None


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
    matched_count = sum(1 for d in documents if d.doc_type == "alert" and d.metadata.get("has_matching_runbook"))

    for mode_report in report.modes.values():
        assert mode_report.overall.n == matched_count


# ------------------------------------------------------------- abstention


def test_abstention_counts_match_the_corpus(report, documents):
    matched = sum(1 for d in documents if d.doc_type == "alert" and d.metadata.get("has_matching_runbook"))
    unmatched = sum(1 for d in documents if d.doc_type == "alert" and not d.metadata.get("has_matching_runbook"))

    for signal in (report.abstention.top1_cosine, report.abstention.gap):
        assert signal.matched.n == matched
        assert signal.unmatched.n == unmatched > 0


def test_abstention_does_not_depend_on_which_modes_were_evaluated(retriever, documents):
    """Guards against abstention being folded into the per-mode evaluation,
    where it would pick up that mode's score scale. (That it is specifically
    *vector cosine* -- not BM25 or the fused score -- is what
    test_abstention_top1_is_the_raw_vector_cosine_of_the_best_runbook checks.)"""
    only_keyword = evaluate_retrieval(retriever, documents, embedder_name="e", modes=["keyword"])
    only_hybrid = evaluate_retrieval(retriever, documents, embedder_name="e", modes=["hybrid"])

    assert only_keyword.abstention == only_hybrid.abstention


def test_abstention_top1_is_the_raw_vector_cosine_of_the_best_runbook(retriever, documents):
    alert = next(d for d in documents if d.doc_type == "alert" and d.metadata.get("has_matching_runbook"))
    expected = retriever.search(alert.body, k=1, where={"doc_type": "runbook"}, mode="vector")[0].score

    single = analyze_abstention(retriever, [alert])

    assert single.top1_cosine.matched.mean == pytest.approx(expected)


def test_abstention_gap_is_top1_minus_top2_and_never_negative(retriever, documents):
    # Pick a case whose top two hits genuinely differ: on a tie the gap is 0
    # either way round, so a flipped subtraction would go unnoticed.
    for alert in (d for d in documents if d.doc_type == "alert" and d.metadata.get("has_matching_runbook")):
        first, second = retriever.search(alert.body, k=2, where={"doc_type": "runbook"}, mode="vector")
        if first.score - second.score > 0.01:
            break
    else:
        pytest.fail("no alert with a distinguishable top-2 found")

    single = analyze_abstention(retriever, [alert])

    assert single.gap.matched.mean == pytest.approx(first.score - second.score)
    assert single.gap.matched.mean > 0.0


def test_abstention_cosine_stays_within_the_valid_cosine_range(report):
    for stats in (report.abstention.top1_cosine.matched, report.abstention.top1_cosine.unmatched):
        assert -1.0 <= stats.min <= stats.max <= 1.0


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
    assert "Abstention analysis" in markdown
    assert "Weakest category" in markdown
    assert "Stale-runbook contamination" in markdown
    assert "Hybrid fusion" in markdown
    assert "Hit@1" in markdown
    assert "Precision@" not in markdown


def test_report_has_one_abstention_section_not_one_per_mode(report):
    markdown = render_markdown(report)

    assert markdown.count("## Abstention analysis") == 1
    assert "#### No-match" not in markdown


def test_report_labels_scores_by_what_they_are_and_never_calls_bm25_or_fused_scores_similarity(report):
    markdown = render_markdown(report)

    assert "Top-1 similarity score" not in markdown
    assert "mean cosine" in markdown
    assert "mean cosine gap" in markdown
    assert "raw vector cosine similarity" in markdown
    assert "BM25" in markdown  # explains why it isn't used, rather than silently dropping it


def test_report_reports_standard_deviation_and_auc_for_both_signals(report):
    markdown = render_markdown(report)

    assert markdown.count("std dev") == 2
    assert markdown.count("AUC = ") == 2
    assert "Signal 1: top-1 cosine similarity" in markdown
    assert "Signal 2: gap between the top two hits" in markdown


def test_report_is_deterministic_apart_from_the_timestamp(retriever, documents):
    a = render_markdown(evaluate_retrieval(retriever, documents, embedder_name="e", modes=["vector"]))
    b = render_markdown(evaluate_retrieval(retriever, documents, embedder_name="e", modes=["vector"]))

    strip_timestamp = lambda s: s.split("\n", 3)[-1]  # drop the "generated ..." line
    assert strip_timestamp(a) == strip_timestamp(b)
