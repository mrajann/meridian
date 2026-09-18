from collections import Counter

import pytest

from meridian.catalog import load_catalog
from meridian.corpus import FRAGILE_SERVICES, generate_corpus, load_corpus, write_corpus
from meridian.corpus.models import CorpusDocument


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def corpus(catalog):
    return generate_corpus(catalog)


def by_id(corpus: list[CorpusDocument]) -> dict[str, CorpusDocument]:
    return {d.doc_id: d for d in corpus}


def test_all_doc_ids_are_unique(corpus):
    ids = [d.doc_id for d in corpus]
    assert len(ids) == len(set(ids))


def test_document_counts_by_type(corpus):
    counts = Counter(d.doc_type for d in corpus)
    # See tests/test_corpus_adversarial.py for the breakdown of how many of
    # these are adversarial vs. baseline reference material.
    assert counts["runbook"] >= 150
    assert counts["postmortem"] >= 80
    assert counts["alert"] >= 100
    assert counts["chat_transcript"] >= 20
    assert counts["catalog_entry"] >= 15
    assert len(corpus) >= 400


def test_every_matched_alert_references_a_real_runbook(corpus):
    runbook_ids = {d.doc_id for d in corpus if d.doc_type == "runbook"}
    alerts = [d for d in corpus if d.doc_type == "alert"]
    for alert in alerts:
        if alert.metadata.get("has_matching_runbook"):
            assert alert.metadata["correct_runbook"] in runbook_ids, alert.doc_id


def test_fragile_services_account_for_roughly_40_percent_of_incidents(corpus):
    # "Incidents" = alerts (a fired incident) + postmortems (its retrospective).
    # Runbooks are reference material and chat transcripts discuss an incident
    # rather than being one, so neither counts toward this ratio.
    incidents = [d for d in corpus if d.doc_type in ("alert", "postmortem")]
    fragile = [d for d in incidents if d.metadata.get("fragile_service") in FRAGILE_SERVICES]

    fraction = len(fragile) / len(incidents)
    assert 0.35 <= fraction <= 0.45, f"expected ~40% fragile-service incidents, got {fraction:.0%}"


def test_catalog_documents_are_derived_from_the_real_catalog(corpus, catalog):
    catalog_docs = [d for d in corpus if d.doc_type == "catalog_entry"]
    assert len(catalog_docs) >= 15

    for doc in catalog_docs:
        service_name = doc.services[0]
        real_entry = catalog[service_name]
        assert real_entry.blast_radius in doc.body
        assert real_entry.description in doc.body


def test_corpus_round_trips_through_disk(tmp_path, corpus):
    write_corpus(corpus, directory=tmp_path)
    reloaded = load_corpus(directory=tmp_path)

    assert len(reloaded) == len(corpus)
    assert {d.doc_id for d in reloaded} == {d.doc_id for d in corpus}

    original = by_id(corpus)
    for doc in reloaded:
        assert doc.body.strip() == original[doc.doc_id].body.strip()
        assert doc.metadata == original[doc.doc_id].metadata
