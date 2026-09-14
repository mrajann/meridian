import difflib
from collections import Counter

import pytest

from meridian.catalog import load_catalog
from meridian.corpus import FRAGILE_SERVICES, generate_corpus
from meridian.corpus.generator import generate_runbooks as generate_runbooks_batch1
from meridian.corpus.models import CorpusDocument
from meridian.corpus.scale import (
    _NEAR_DUP_SPECS,
    generate_alerts_v2,
    generate_catalog_documents_v2,
    generate_postmortems_v2,
    generate_runbooks_v2,
)
from meridian.graph import DependencyGraph


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def runbooks_v2(catalog):
    return generate_runbooks_v2(catalog)


@pytest.fixture(scope="module")
def postmortems_v2(catalog):
    return generate_postmortems_v2(catalog)


@pytest.fixture(scope="module")
def alerts_v2(catalog, runbooks_v2):
    all_runbooks = [*generate_runbooks_batch1(), *runbooks_v2]
    return generate_alerts_v2(catalog, all_runbooks)


@pytest.fixture(scope="module")
def full_corpus(catalog):
    return generate_corpus(catalog)


def by_id(docs: list[CorpusDocument]) -> dict[str, CorpusDocument]:
    return {d.doc_id: d for d in docs}


# --- Batch sizes ---


def test_batch2_document_counts(runbooks_v2, postmortems_v2, alerts_v2, catalog):
    assert len(runbooks_v2) == 100
    assert len(postmortems_v2) == 75
    assert len(alerts_v2) == 50
    assert len(generate_catalog_documents_v2(catalog)) == 15


def test_full_corpus_combines_both_batches(full_corpus):
    counts = Counter(d.doc_type for d in full_corpus)
    # batch1 (12/9/6/3/2) + batch2 (100/75/50/25/15)
    assert counts == {
        "runbook": 112,
        "postmortem": 84,
        "alert": 56,
        "chat_transcript": 28,
        "catalog_entry": 17,
    }
    assert len(full_corpus) == 297


def test_no_doc_id_collisions_across_batches(full_corpus):
    ids = [d.doc_id for d in full_corpus]
    assert len(ids) == len(set(ids))


def test_batch2_catalog_docs_dont_duplicate_batch1(catalog):
    batch2_services = {d.services[0] for d in generate_catalog_documents_v2(catalog)}
    assert batch2_services.isdisjoint({"postgres-primary", "notification-service"})


# --- Adversarial case: near-duplicate runbooks, at scale (10 pairs) ---


def test_all_ten_near_duplicate_pairs_are_textually_similar(runbooks_v2):
    docs = by_id(runbooks_v2)
    for spec in _NEAR_DUP_SPECS:
        a = docs[f"runbook-{spec['service']}-{spec['category']}-{spec['id_a']}"]
        b = docs[f"runbook-{spec['service']}-{spec['category']}-{spec['id_b']}"]
        ratio = difflib.SequenceMatcher(None, a.body, b.body).ratio()
        assert ratio > 0.55, f"{spec['service']}: expected near-duplicate, got similarity {ratio:.2f}"
        assert a.metadata["root_cause_category"] != b.metadata["root_cause_category"]


# --- Adversarial case: no matching runbook, ~10% of alerts ---


def test_batch2_no_matching_runbook_rate_is_roughly_ten_percent(alerts_v2):
    unmatched = [a for a in alerts_v2 if not a.metadata["has_matching_runbook"]]
    fraction = len(unmatched) / len(alerts_v2)
    assert 0.05 <= fraction <= 0.15, f"expected ~10% unmatched, got {fraction:.0%}"


def test_batch2_unmatched_alerts_genuinely_have_no_match(alerts_v2, runbooks_v2, catalog):
    all_runbooks = [*generate_runbooks_batch1(), *runbooks_v2]
    unmatched = [a for a in alerts_v2 if not a.metadata["has_matching_runbook"]]
    assert len(unmatched) >= 1

    for alert in unmatched:
        assert alert.metadata["correct_runbook"] is None
        service = alert.metadata["root_cause_service"]
        category = alert.metadata["root_cause_category"]
        matches = [
            r for r in all_runbooks if service in r.services and r.metadata.get("root_cause_category") == category
        ]
        assert matches == [], f"{alert.doc_id}: expected no match, found {[m.doc_id for m in matches]}"


def test_every_matched_alert_references_a_real_runbook(alerts_v2, runbooks_v2):
    real_ids = {r.doc_id for r in [*generate_runbooks_batch1(), *runbooks_v2]}
    for alert in alerts_v2:
        if alert.metadata["has_matching_runbook"]:
            assert alert.metadata["correct_runbook"] in real_ids


# --- Adversarial case: cascading failure, two independent postgres-primary cascades ---


def test_two_cascades_each_cover_six_real_dependents_and_dont_overlap(postmortems_v2, catalog):
    cascades = [p for p in postmortems_v2 if len(p.metadata.get("affected_services", [])) >= 6]
    assert len(cascades) == 2

    real_dependents = DependencyGraph(catalog).dependents("postgres-primary")
    subsets = []
    for postmortem in cascades:
        assert postmortem.metadata["root_cause_service"] == "postgres-primary"
        affected = postmortem.metadata["affected_services"]
        assert set(affected).issubset(real_dependents)
        subsets.append(set(affected))

    assert subsets[0].isdisjoint(subsets[1]), "the two cascades should cover different services"


# --- Adversarial case: stale runbooks (batch2 adds 3 more decommissioned services) ---


def test_batch2_stale_runbooks_reference_decommissioned_services(runbooks_v2, catalog):
    stale = [d for d in runbooks_v2 if "stale_reference" in d.metadata]
    assert len(stale) == 6  # 3 decommissioned services x 2 runbooks each
    for doc in stale:
        assert doc.metadata["stale_reference"] not in catalog


# --- Fragile-service weighting: exact at this scale ---


def test_batch2_fragile_weighting_is_close_to_40_percent(postmortems_v2, alerts_v2):
    incidents = [*postmortems_v2, *alerts_v2]
    fragile = [d for d in incidents if d.metadata.get("fragile_service") in FRAGILE_SERVICES]
    fraction = len(fragile) / len(incidents)
    assert 0.35 <= fraction <= 0.45, f"expected ~40%, got {fraction:.0%}"


def test_combined_corpus_fragile_weighting_is_40_percent(full_corpus):
    incidents = [d for d in full_corpus if d.doc_type in ("alert", "postmortem")]
    fragile = [d for d in incidents if d.metadata.get("fragile_service") in FRAGILE_SERVICES]
    fraction = len(fragile) / len(incidents)
    assert 0.35 <= fraction <= 0.45, f"expected ~40%, got {fraction:.0%}"


# --- Round trip for the full combined corpus ---


def test_full_corpus_round_trips_through_disk(tmp_path, full_corpus):
    from meridian.corpus import load_corpus, write_corpus

    write_corpus(full_corpus, directory=tmp_path)
    reloaded = load_corpus(directory=tmp_path)

    assert len(reloaded) == len(full_corpus)
    assert {d.doc_id for d in reloaded} == {d.doc_id for d in full_corpus}
