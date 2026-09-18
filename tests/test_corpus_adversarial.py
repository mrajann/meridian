"""Verifies each adversarial category from spec section 3 is a first-class,
independently-targeted part of corpus generation -- not a handful of
hand-seeded examples that bulk generation doesn't reproduce. Each test here
asserts a minimum count against the real generated corpus, so a future
change to the generator that quietly drops a category's volume fails CI
instead of only showing up if someone happens to look.
"""

import difflib

import pytest

from meridian.catalog import load_catalog
from meridian.corpus import (
    CASCADING_FAILURE_SET_COUNT,
    NEAR_DUPLICATE_PAIR_COUNT,
    NO_MATCHING_RUNBOOK_COUNT,
    STALE_RUNBOOK_COUNT,
    VOCABULARY_MISMATCH_COUNT,
    generate_corpus,
)
from meridian.corpus.models import CorpusDocument
from meridian.corpus.synonyms import SYNONYM_PAIRS
from meridian.graph import DependencyGraph

# Floors, not exact targets: generation is deterministic so these should
# match the constants exactly today, but a test pinned to "==" would fail
# for the wrong reason if someone deliberately raises a target later.
MIN_NEAR_DUPLICATE_PAIRS = 25
MIN_VOCABULARY_MISMATCH_CASES = 25
MIN_NO_MATCHING_RUNBOOK = 15
MIN_CASCADING_FAILURE_SETS = 12
MIN_STALE_RUNBOOKS = 10


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def corpus(catalog):
    return generate_corpus(catalog)


def by_id(corpus: list[CorpusDocument]) -> dict[str, CorpusDocument]:
    return {d.doc_id: d for d in corpus}


def by_case(corpus: list[CorpusDocument], case: str) -> list[CorpusDocument]:
    return [d for d in corpus if d.metadata.get("adversarial_case") == case]


# ============================================================
# 1. Near-duplicate runbook pairs
# ============================================================


def test_near_duplicate_pair_count_meets_target(corpus):
    alerts = [d for d in by_case(corpus, "near_duplicate_pair") if d.doc_type == "alert"]
    assert len(alerts) >= MIN_NEAR_DUPLICATE_PAIRS
    assert len(alerts) == NEAR_DUPLICATE_PAIR_COUNT


def test_every_near_duplicate_pair_is_textually_similar_but_differs_in_root_cause(corpus):
    docs = by_id(corpus)
    alerts = [d for d in by_case(corpus, "near_duplicate_pair") if d.doc_type == "alert"]
    assert len(alerts) >= MIN_NEAR_DUPLICATE_PAIRS

    for alert in alerts:
        correct = docs[alert.metadata["correct_runbook"]]
        service = correct.services[0]
        correct_category = correct.metadata["root_cause_category"]
        base_category = correct_category.split("__")[0]

        siblings = [
            d
            for d in corpus
            if d.doc_type == "runbook"
            and d.services == [service]
            and d.doc_id != correct.doc_id
            and d.metadata.get("root_cause_category", "").split("__")[0] == base_category
            and "__" in d.metadata.get("root_cause_category", "")
        ]
        assert len(siblings) == 1, f"{correct.doc_id}: expected exactly one near-dup sibling, got {len(siblings)}"
        sibling = siblings[0]

        similarity = difflib.SequenceMatcher(None, correct.body, sibling.body).ratio()
        assert similarity > 0.55, f"{correct.doc_id}/{sibling.doc_id}: similarity only {similarity:.2f}"
        assert correct.metadata["root_cause_category"] != sibling.metadata["root_cause_category"]


def test_near_duplicate_alert_points_only_at_the_correct_half_of_its_pair(corpus):
    """Concrete example: the checkout-api near-duplicate pair specifically."""
    docs = by_id(corpus)
    alert = docs["alert-near-dup-checkout-api"]
    correct = docs[alert.metadata["correct_runbook"]]
    assert correct.doc_id.startswith("runbook-checkout-api-")
    assert alert.metadata["has_matching_runbook"] is True


# ============================================================
# 2. Vocabulary-mismatch cases
# ============================================================


def test_vocabulary_mismatch_count_meets_target(corpus):
    alerts = [d for d in by_case(corpus, "vocabulary_mismatch") if d.doc_type == "alert"]
    assert len(alerts) >= MIN_VOCABULARY_MISMATCH_CASES
    assert len(alerts) == VOCABULARY_MISMATCH_COUNT


def test_every_vocabulary_mismatch_case_has_zero_shared_key_phrase(corpus):
    docs = by_id(corpus)
    alerts = [d for d in by_case(corpus, "vocabulary_mismatch") if d.doc_type == "alert"]
    assert len(alerts) >= MIN_VOCABULARY_MISMATCH_CASES

    for alert in alerts:
        runbook = docs[alert.metadata["correct_runbook"]]
        alert_text, runbook_text = alert.body.lower(), runbook.body.lower()

        pair = next(p for p in SYNONYM_PAIRS if p["alert_phrase"].lower() in alert_text)
        assert pair["alert_phrase"].lower() in alert_text
        assert pair["runbook_phrase"].lower() in runbook_text
        assert pair["runbook_phrase"].lower() not in alert_text, alert.doc_id
        assert pair["alert_phrase"].lower() not in runbook_text, alert.doc_id


def test_connection_pool_vocabulary_mismatch_example_matches_spec(corpus):
    """Concrete example: the spec's own connection-pool phrasing, verbatim."""
    matches = [
        d
        for d in by_case(corpus, "vocabulary_mismatch")
        if d.doc_type == "alert" and "connection pool exhausted" in d.body.lower()
    ]
    assert len(matches) >= 1
    alert = matches[0]
    runbook = by_id(corpus)[alert.metadata["correct_runbook"]]
    assert "database connections maxed out" in runbook.body.lower()
    assert "database connections maxed out" not in alert.body.lower()
    assert "connection pool exhausted" not in runbook.body.lower()


# ============================================================
# 3. No-matching-runbook incidents
# ============================================================


def test_no_matching_runbook_count_meets_target(corpus):
    alerts = by_case(corpus, "no_matching_runbook")
    assert len(alerts) >= MIN_NO_MATCHING_RUNBOOK
    assert len(alerts) == NO_MATCHING_RUNBOOK_COUNT


def test_every_no_matching_runbook_alert_is_genuinely_unmatched(corpus):
    runbooks = [d for d in corpus if d.doc_type == "runbook"]
    alerts = by_case(corpus, "no_matching_runbook")
    assert len(alerts) >= MIN_NO_MATCHING_RUNBOOK

    for alert in alerts:
        assert alert.metadata["has_matching_runbook"] is False
        assert alert.metadata["correct_runbook"] is None

        service = alert.metadata["root_cause_service"]
        category = alert.metadata["root_cause_category"]
        matches = [
            r
            for r in runbooks
            if service in r.services and r.metadata.get("root_cause_category") == category
        ]
        assert matches == [], f"{alert.doc_id}: expected no match, found {[m.doc_id for m in matches]}"


def test_overall_no_matching_runbook_rate_is_close_to_ten_percent(corpus):
    alerts = [d for d in corpus if d.doc_type == "alert"]
    unmatched = [a for a in alerts if not a.metadata["has_matching_runbook"]]
    fraction = len(unmatched) / len(alerts)
    assert 0.07 <= fraction <= 0.15, f"expected ~10% unmatched, got {fraction:.0%}"


# ============================================================
# 4. Cascading-failure sets
# ============================================================


def test_cascading_failure_set_count_meets_target(corpus):
    postmortems = by_case(corpus, "cascading_failure")
    postmortems = [d for d in postmortems if d.doc_type == "postmortem"]
    assert len(postmortems) >= MIN_CASCADING_FAILURE_SETS
    assert len(postmortems) == CASCADING_FAILURE_SET_COUNT


def test_every_cascade_covers_six_real_dependents_of_its_hub(corpus, catalog):
    graph = DependencyGraph(catalog)
    postmortems = [d for d in by_case(corpus, "cascading_failure") if d.doc_type == "postmortem"]
    assert len(postmortems) >= MIN_CASCADING_FAILURE_SETS

    for postmortem in postmortems:
        hub = postmortem.metadata["root_cause_service"]
        affected = postmortem.metadata["affected_services"]
        assert len(affected) >= 6, postmortem.doc_id
        real_dependents = graph.dependents(hub)
        assert set(affected).issubset(real_dependents), f"{postmortem.doc_id}: fabricated dependents"


def test_cascades_from_the_same_hub_dont_overlap(corpus):
    postmortems = [d for d in by_case(corpus, "cascading_failure") if d.doc_type == "postmortem"]
    by_hub: dict[str, list[set[str]]] = {}
    for postmortem in postmortems:
        hub = postmortem.metadata["root_cause_service"]
        by_hub.setdefault(hub, []).append(set(postmortem.metadata["affected_services"]))

    for hub, subsets in by_hub.items():
        for i in range(len(subsets)):
            for j in range(i + 1, len(subsets)):
                assert subsets[i].isdisjoint(subsets[j]), f"{hub}: cascades {i} and {j} overlap"


def test_postgres_primary_cascade_example_is_one_postmortem_covering_six_services(corpus):
    """Concrete example: the spec's canonical postgres-primary case."""
    postmortems = [
        d
        for d in by_case(corpus, "cascading_failure")
        if d.doc_type == "postmortem" and d.metadata["root_cause_service"] == "postgres-primary"
    ]
    assert len(postmortems) >= 1
    example = postmortems[0]
    assert len(example.metadata["affected_services"]) == 6
    assert "one incident, not" in example.body


def test_every_cascade_alert_has_a_real_matching_runbook(corpus):
    runbook_ids = {d.doc_id for d in corpus if d.doc_type == "runbook"}
    alerts = [d for d in by_case(corpus, "cascading_failure") if d.doc_type == "alert"]
    assert len(alerts) >= MIN_CASCADING_FAILURE_SETS
    for alert in alerts:
        assert alert.metadata["has_matching_runbook"] is True
        assert alert.metadata["correct_runbook"] in runbook_ids


# ============================================================
# 5. Stale runbooks
# ============================================================


def test_stale_runbook_count_meets_target(corpus):
    stale = by_case(corpus, "stale_runbook")
    assert len(stale) >= MIN_STALE_RUNBOOKS
    assert len(stale) == STALE_RUNBOOK_COUNT


def test_every_stale_runbook_references_a_genuinely_decommissioned_service(corpus, catalog):
    stale = by_case(corpus, "stale_runbook")
    assert len(stale) >= MIN_STALE_RUNBOOKS
    for doc in stale:
        referenced = doc.metadata["stale_reference"]
        assert referenced not in catalog, f"{referenced} should not exist in the real catalog"
        assert referenced in doc.body


def test_stale_runbooks_cover_multiple_distinct_decommissioned_services(corpus):
    stale = by_case(corpus, "stale_runbook")
    distinct = {d.metadata["stale_reference"] for d in stale}
    assert len(distinct) >= 3, "expected stale runbooks spread across several decommissioned services, not one"
