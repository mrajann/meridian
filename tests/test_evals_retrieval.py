import pytest

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.corpus.models import CorpusDocument
from meridian.evals import (
    build_eval_cases,
    evaluate_retrieval,
    render_markdown,
)
from meridian.evals.retrieval import BASELINE_CATEGORY, CaseResult, EvalCase, Metrics, NoMatchAnalysis, ScoreStats, _aggregate
from meridian.indexing import HashingEmbedder, VectorIndex, build_index
from meridian.indexing.store import Hit
from meridian.retrieval import Retriever

# Measured with HashingEmbedder when this suite was written: vector overall
# recall@5 0.743, keyword 0.771, hybrid 0.761 (n=109 matched). Floors here are
# regression guards -- "the pipeline still works and is in the right
# ballpark" -- not quality targets; cascading_failure is *expected* to score
# poorly (see its own test) so it has no floor.
MIN_OVERALL_RECALL_AT_5 = {"vector": 0.6, "keyword": 0.6, "hybrid": 0.6}
MIN_NEAR_DUPLICATE_RECALL_AT_5 = 0.75
MIN_VOCABULARY_MISMATCH_RECALL_AT_5 = 0.7


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

    assert metrics == Metrics(n=2, precision_at_k=0.2, recall_at_k=1.0, mrr=1.0)


def test_aggregate_of_all_misses_is_zero():
    metrics = _aggregate([_result(None), _result(None)], k=5)

    assert metrics == Metrics(n=2, precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)


def test_aggregate_rank_beyond_k_counts_for_mrr_but_not_precision_or_recall():
    metrics = _aggregate([_result(8)], k=5)

    assert metrics.precision_at_k == 0.0
    assert metrics.recall_at_k == 0.0
    assert metrics.mrr == pytest.approx(1 / 8)


def test_aggregate_of_no_results_is_all_zero():
    assert _aggregate([], k=5) == Metrics(n=0, precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)


def test_mrr_is_the_mean_reciprocal_rank():
    metrics = _aggregate([_result(1), _result(2), _result(None)], k=5)

    assert metrics.mrr == pytest.approx((1 / 1 + 1 / 2 + 0) / 3)


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


# -------------------------------------------------------------- end to end


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid"])
def test_overall_recall_meets_the_regression_floor(report, mode):
    assert report.modes[mode].overall.recall_at_k >= MIN_OVERALL_RECALL_AT_5[mode]


def test_near_duplicate_pairs_are_found_well_above_baseline(report):
    vector = report.modes["vector"]
    near_dup = vector.by_category["near_duplicate_pair"].recall_at_k
    baseline = vector.by_category[BASELINE_CATEGORY].recall_at_k

    assert near_dup >= MIN_NEAR_DUPLICATE_RECALL_AT_5
    assert near_dup > baseline, "the near-duplicate case should be easy to match by design, not merely typical"


def test_vocabulary_mismatch_is_reported_separately_and_meets_its_floor(report):
    assert report.modes["vector"].by_category["vocabulary_mismatch"].recall_at_k >= MIN_VOCABULARY_MISMATCH_RECALL_AT_5


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


def test_no_match_incidents_are_excluded_from_precision_recall_mrr(report, documents):
    unmatched_count = sum(1 for d in documents if d.doc_type == "alert" and not d.metadata.get("has_matching_runbook"))
    matched_count = sum(1 for d in documents if d.doc_type == "alert" and d.metadata.get("has_matching_runbook"))

    for mode_report in report.modes.values():
        assert mode_report.overall.n == matched_count
        assert mode_report.no_match.unmatched.n == unmatched_count


def test_no_match_analysis_has_a_score_for_every_unmatched_incident(report, documents):
    unmatched_count = sum(1 for d in documents if d.doc_type == "alert" and not d.metadata.get("has_matching_runbook"))

    assert report.modes["vector"].no_match.unmatched.n == unmatched_count > 0


# -------------------------------------------------------------------- report


def test_rendered_report_includes_every_mode_and_category(report):
    markdown = render_markdown(report)

    for mode in ("vector", "keyword", "hybrid"):
        assert f"`{mode}`" in markdown
    for label in ("near-duplicate runbook pair", "vocabulary mismatch", "cascading failure", "baseline"):
        assert label in markdown
    assert "No-match / abstention" in markdown
    assert "Weakest category" in markdown


def test_report_is_deterministic_apart_from_the_timestamp(retriever, documents):
    a = render_markdown(evaluate_retrieval(retriever, documents, embedder_name="e", modes=["vector"]))
    b = render_markdown(evaluate_retrieval(retriever, documents, embedder_name="e", modes=["vector"]))

    strip_timestamp = lambda s: s.split("\n", 3)[-1]  # drop the "generated ..." line
    assert strip_timestamp(a) == strip_timestamp(b)
