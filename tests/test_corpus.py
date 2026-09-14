import difflib
from collections import Counter

import pytest

from meridian.catalog import load_catalog
from meridian.corpus import DECOMMISSIONED_SERVICES, FRAGILE_SERVICES, load_corpus, write_corpus
from meridian.corpus.generator import generate_corpus as generate_corpus_batch1
from meridian.corpus.models import CorpusDocument


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def corpus(catalog):
    # Pinned to the original 32-document hand-authored batch specifically --
    # see test_corpus_scale.py for the larger template-generated batch and
    # for meridian.corpus.generate_corpus(), which returns both combined.
    return generate_corpus_batch1(catalog)


def by_id(corpus: list[CorpusDocument]) -> dict[str, CorpusDocument]:
    return {d.doc_id: d for d in corpus}


# --- Basic shape ---


def test_corpus_has_expected_document_counts(corpus):
    counts = Counter(d.doc_type for d in corpus)
    assert counts == {
        "runbook": 12,
        "postmortem": 9,
        "alert": 6,
        "chat_transcript": 3,
        "catalog_entry": 2,
    }
    assert len(corpus) == 32


def test_all_doc_ids_are_unique(corpus):
    ids = [d.doc_id for d in corpus]
    assert len(ids) == len(set(ids))


# --- Adversarial case: near-duplicate runbooks ---


def test_near_duplicate_runbooks_are_textually_similar_but_differ_in_root_cause(corpus):
    docs = by_id(corpus)
    database = docs["runbook-checkout-5xx-database"]
    upstream = docs["runbook-checkout-5xx-upstream"]

    similarity = difflib.SequenceMatcher(None, database.body, upstream.body).ratio()
    assert similarity > 0.6, f"expected near-duplicate runbooks, got similarity {similarity:.2f}"

    assert database.metadata["root_cause_category"] != upstream.metadata["root_cause_category"]


def test_only_the_correct_near_duplicate_runbook_is_referenced_by_the_alert(corpus):
    docs = by_id(corpus)
    alert = docs["alert-checkout-api-p99-latency"]

    assert alert.metadata["correct_runbook"] == "runbook-checkout-5xx-database"
    assert alert.metadata["correct_runbook"] != "runbook-checkout-5xx-upstream"


# --- Adversarial case: vocabulary mismatch ---


def test_alert_and_correct_runbook_use_non_overlapping_key_terms(corpus):
    docs = by_id(corpus)
    alert = docs["alert-checkout-api-p99-latency"]
    runbook = docs["runbook-checkout-5xx-database"]

    alert_text = alert.body.lower()
    runbook_text = runbook.body.lower()

    assert "exhausted" in alert_text
    assert "maxed out" not in alert_text

    assert "maxed out" in runbook_text
    assert "exhausted" not in runbook_text


# --- Adversarial case: no matching runbook ---


def test_roughly_ten_percent_of_alerts_have_no_matching_runbook(corpus):
    alerts = [d for d in corpus if d.doc_type == "alert"]
    unmatched = [a for a in alerts if not a.metadata["has_matching_runbook"]]

    # 1 of 6 (~17%) is the closest achievable approximation of "roughly 10%"
    # at this corpus's small scale; the full 200-alert corpus can hit 10% exactly.
    assert len(unmatched) >= 1
    assert len(unmatched) / len(alerts) <= 0.25


def test_no_matching_runbook_alert_genuinely_has_no_match_in_the_corpus(corpus):
    docs = by_id(corpus)
    alert = docs["alert-search-service-zero-results"]
    assert alert.metadata["has_matching_runbook"] is False
    assert alert.metadata["correct_runbook"] is None

    runbooks = [d for d in corpus if d.doc_type == "runbook"]
    target_service = alert.metadata["root_cause_service"]
    target_category = alert.metadata["root_cause_category"]

    matches = [
        r
        for r in runbooks
        if target_service in r.services and r.metadata.get("root_cause_category") == target_category
    ]
    assert matches == [], f"expected no runbook to match, found {[m.doc_id for m in matches]}"


# --- Adversarial case: cascading failure ---


def test_cascade_postmortem_covers_at_least_six_dependent_services(corpus, catalog):
    docs = by_id(corpus)
    postmortem = docs["postmortem-postgres-primary-disk-full-cascade"]

    assert postmortem.metadata["root_cause_service"] == "postgres-primary"
    affected = postmortem.metadata["affected_services"]
    assert len(affected) >= 6

    from meridian.graph import DependencyGraph

    real_dependents = DependencyGraph(catalog).dependents("postgres-primary")
    assert set(affected).issubset(real_dependents), "cascade services must be real dependents, not fabricated"


def test_cascade_is_one_postmortem_not_one_per_affected_service(corpus):
    postmortems = [d for d in corpus if d.doc_type == "postmortem"]
    postgres_primary_postmortems = [
        p for p in postmortems if p.metadata["root_cause_service"] == "postgres-primary"
    ]
    assert len(postgres_primary_postmortems) == 1


# --- Adversarial case: stale runbooks ---


def test_stale_runbooks_reference_decommissioned_services(corpus, catalog):
    stale = [d for d in corpus if d.doc_type == "runbook" and "stale_reference" in d.metadata]

    assert len(stale) >= 2, "expected at least a couple of stale runbooks"
    for doc in stale:
        referenced = doc.metadata["stale_reference"]
        assert referenced in DECOMMISSIONED_SERVICES
        assert referenced not in catalog, f"{referenced} should not exist in the real catalog"


# --- Fragile-service weighting (~40% of incidents) ---


def test_fragile_services_account_for_roughly_40_percent_of_incidents(corpus):
    # "Incidents" = alerts (a fired incident) + postmortems (its retrospective).
    # Runbooks are reference material and chat transcripts discuss an incident
    # rather than being one, so neither counts toward this ratio.
    incidents = [d for d in corpus if d.doc_type in ("alert", "postmortem")]
    fragile = [d for d in incidents if d.metadata.get("fragile_service") in FRAGILE_SERVICES]

    fraction = len(fragile) / len(incidents)
    assert 0.3 <= fraction <= 0.5, f"expected ~40% fragile-service incidents, got {fraction:.0%}"


def test_fragile_service_field_is_always_one_of_the_three_or_none(corpus):
    incidents = [d for d in corpus if d.doc_type in ("alert", "postmortem")]
    for doc in incidents:
        value = doc.metadata.get("fragile_service")
        assert value is None or value in FRAGILE_SERVICES


# --- Catalog-derived documents ---


def test_catalog_documents_are_derived_from_the_real_catalog(corpus, catalog):
    catalog_docs = [d for d in corpus if d.doc_type == "catalog_entry"]
    assert len(catalog_docs) == 2

    for doc in catalog_docs:
        service_name = doc.services[0]
        real_entry = catalog[service_name]
        assert real_entry.blast_radius in doc.body
        assert real_entry.description in doc.body


# --- Disk round-trip ---


def test_corpus_round_trips_through_disk(tmp_path, corpus):
    write_corpus(corpus, directory=tmp_path)
    reloaded = load_corpus(directory=tmp_path)

    assert len(reloaded) == len(corpus)
    assert {d.doc_id for d in reloaded} == {d.doc_id for d in corpus}

    original = by_id(corpus)
    for doc in reloaded:
        assert doc.body.strip() == original[doc.doc_id].body.strip()
        assert doc.metadata == original[doc.doc_id].metadata
