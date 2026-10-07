import pytest

from meridian.catalog import load_catalog
from meridian.config import Settings
from meridian.corpus import generate_corpus
from meridian.indexing import (
    EmbedderMismatchError,
    HashingEmbedder,
    IndexNotBuiltError,
    VectorIndex,
    build_filter,
    build_index,
    chunk_budget,
    chunk_corpus,
    chunk_metadata,
)
from meridian.indexing.__main__ import main as cli_main

# Ground-truth labels on corpus documents. If any reached the index, a
# retriever could filter on the answer and every retrieval eval would be moot.
GROUND_TRUTH_KEYS = {
    "correct_runbook",
    "has_matching_runbook",
    "root_cause_service",
    "root_cause_category",
    "adversarial_case",
    "fragile_service",
    "stale_reference",
    "affected_services",
}


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def documents(catalog):
    return generate_corpus(catalog)


@pytest.fixture(scope="module")
def embedder():
    return HashingEmbedder()


@pytest.fixture(scope="module")
def built(tmp_path_factory, catalog, documents, embedder):
    index = VectorIndex(tmp_path_factory.mktemp("chroma"), embedder)
    stats = build_index(documents, catalog, embedder, index)
    return index, stats


def all_hits(index):
    return index.query("incident", k=index.count())


# ------------------------------------------------------------- build stats


def test_index_holds_every_chunk(built, documents, embedder):
    index, stats = built
    chunks = chunk_corpus(documents, embedder.count_tokens, chunk_budget(embedder))

    assert index.count() == stats.chunks == len(chunks)
    assert stats.documents == len(documents)


def test_no_embedded_chunk_exceeds_the_budget(built, embedder):
    _, stats = built

    assert stats.over_budget == []
    assert stats.max_embed_tokens <= stats.chunk_budget < embedder.max_input_tokens


def test_postmortems_are_indexed_by_section_and_other_types_stay_whole(built, documents):
    hits = all_hits(built[0])
    sections_by_doc: dict[str, set[str]] = {}
    chunks_by_doc: dict[str, int] = {}
    for hit in hits:
        chunks_by_doc[hit.doc_id] = chunks_by_doc.get(hit.doc_id, 0) + 1
        if "section" in hit.metadata:
            sections_by_doc.setdefault(hit.doc_id, set()).add(hit.metadata["section"])

    for doc in documents:
        if doc.doc_type == "postmortem":
            assert {"Summary", "Root cause"} <= sections_by_doc[doc.doc_id], doc.doc_id
        else:
            assert chunks_by_doc[doc.doc_id] == 1, f"{doc.doc_id} unexpectedly split"


# ---------------------------------------------------------------- metadata


def test_every_chunk_has_filterable_metadata(built):
    for hit in all_hits(built[0]):
        for key in ("doc_id", "doc_type", "service", "services", "tier", "chunk_index", "chunk_count"):
            assert key in hit.metadata, f"{hit.chunk_id} missing {key}"


def test_no_ground_truth_labels_reach_the_index(built):
    for hit in all_hits(built[0]):
        assert GROUND_TRUTH_KEYS.isdisjoint(hit.metadata), hit.chunk_id


def test_chunk_metadata_is_an_allowlist_not_a_copy_of_document_metadata(catalog, documents, embedder):
    alert = next(d for d in documents if d.doc_type == "alert" and "correct_runbook" in d.metadata)
    chunk = chunk_corpus([alert], embedder.count_tokens, chunk_budget(embedder))[0]

    metadata = chunk_metadata(chunk, 1, catalog)

    assert GROUND_TRUTH_KEYS.isdisjoint(metadata)
    assert metadata["doc_type"] == "alert"


def test_tier_comes_from_the_catalog_entry_of_the_primary_service(built, catalog):
    for hit in all_hits(built[0]):
        service = hit.metadata["service"]
        expected = str(catalog[service].tier) if service in catalog else "unknown"
        assert hit.metadata["tier"] == expected, hit.chunk_id


# ----------------------------------------------------------------- filters


def test_filter_by_doc_type(built):
    hits = built[0].query("incident", k=500, where=build_filter(doc_type="runbook"))

    assert hits and {h.metadata["doc_type"] for h in hits} == {"runbook"}


def test_filter_by_multiple_doc_types(built):
    hits = built[0].query("incident", k=500, where=build_filter(doc_type=["alert", "postmortem"]))

    assert {h.metadata["doc_type"] for h in hits} == {"alert", "postmortem"}


def test_filter_by_service_matches_any_service_a_document_lists(built, documents):
    cascade = next(
        d for d in documents if d.doc_type == "alert" and d.metadata.get("adversarial_case") == "cascading_failure"
    )
    secondary = cascade.services[1]  # affected by the cascade but not the document's primary service

    hits = built[0].query("incident", k=500, where=build_filter(doc_type="alert", service=secondary))

    assert cascade.doc_id in {h.doc_id for h in hits}
    assert all(secondary in h.metadata["services"] for h in hits)


def test_filter_by_tier(built):
    tier_one = built[0].query("incident", k=1000, where=build_filter(tier=1))
    tier_one_or_two = built[0].query("incident", k=1000, where=build_filter(tier=["1", "2"]))

    assert tier_one and {h.metadata["tier"] for h in tier_one} == {"1"}
    assert {h.metadata["tier"] for h in tier_one_or_two} == {"1", "2"}


def test_external_services_are_filterable_as_their_own_tier(built, catalog):
    hits = built[0].query("incident", k=1000, where=build_filter(tier="external"))

    assert hits
    assert all(catalog[h.metadata["service"]].tier == "external" for h in hits)


def test_stale_runbooks_have_unknown_tier(built, catalog):
    hits = built[0].query("incident", k=1000, where=build_filter(doc_type="runbook", tier="unknown"))

    assert hits, "stale runbooks reference services missing from the catalog"
    assert all(h.metadata["service"] not in catalog for h in hits)


def test_filters_combine(built):
    hits = built[0].query("incident", k=1000, where=build_filter(doc_type="runbook", tier="1"))

    assert hits
    assert {(h.metadata["doc_type"], h.metadata["tier"]) for h in hits} == {("runbook", "1")}


def test_no_filters_means_no_where_clause():
    assert build_filter() is None


# ------------------------------------------------------------------ search


def test_results_are_ordered_by_descending_similarity_and_respect_k(built):
    hits = built[0].query("database connections maxed out", k=7)

    assert len(hits) == 7
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_a_runbook_is_the_top_hit_for_its_own_text(built, documents):
    index = built[0]
    runbooks = [d for d in documents if d.metadata.get("adversarial_case") == "vocabulary_mismatch" and d.doc_type == "runbook"]

    for runbook in runbooks:
        top = index.query(runbook.body, k=1, where=build_filter(doc_type="runbook"))[0]
        assert top.doc_id == runbook.doc_id


# -------------------------------------------------- persistence + safety


def test_index_persists_to_disk(tmp_path, catalog, documents, embedder):
    build_index(documents, catalog, embedder, VectorIndex(tmp_path, embedder))

    reopened = VectorIndex(tmp_path, HashingEmbedder())

    assert reopened.count() > 0
    assert reopened.query("connection pool", k=3)


def test_rebuild_replaces_rather_than_accumulates(tmp_path, catalog, documents, embedder):
    index = VectorIndex(tmp_path, embedder)

    first = build_index(documents, catalog, embedder, index)
    second = build_index(documents, catalog, embedder, index)

    assert index.count() == first.chunks == second.chunks


def test_querying_with_a_different_embedder_fails_loudly(tmp_path, catalog, documents):
    build_index(documents, catalog, HashingEmbedder(dimension=256), VectorIndex(tmp_path, HashingEmbedder(dimension=256)))

    with pytest.raises(EmbedderMismatchError, match="hashing-256"):
        VectorIndex(tmp_path, HashingEmbedder(dimension=128)).query("anything")


def test_querying_before_building_says_how_to_build(tmp_path, embedder):
    with pytest.raises(IndexNotBuiltError, match="python -m meridian.indexing build"):
        VectorIndex(tmp_path, embedder).query("anything")


def test_build_refuses_chunks_the_embedder_would_silently_truncate(tmp_path, catalog, documents):
    # A 10-token model can't hold even a header; better to fail than embed a stump.
    tiny = HashingEmbedder(max_input_tokens=10)

    with pytest.raises(ValueError, match="exceed the embedder's input limit"):
        build_index(documents, catalog, tiny, VectorIndex(tmp_path, tiny))


# --------------------------------------------------------------------- CLI


def test_cli_builds_and_queries(tmp_path, monkeypatch, capsys):
    settings = Settings(embedding_backend="hashing", chroma_persist_dir=tmp_path, _env_file=None)
    monkeypatch.setattr("meridian.indexing.__main__.settings", settings)

    cli_main(["build"])
    built_output = capsys.readouterr().out
    cli_main(["query", "database connections maxed out", "--type", "runbook", "--tier", "1", "-k", "3"])
    query_output = capsys.readouterr().out

    assert "indexed" in built_output and "chunks by type" in built_output
    assert query_output.count("runbook  tier=1") == 3


# --------------------------------------------------- cosine_similarities


def test_cosine_similarities_agree_with_the_scores_search_returns(built):
    index = built[0]
    hits = index.query("database connections maxed out", k=5)

    cosines = index.cosine_similarities("database connections maxed out", [h.chunk_id for h in hits])

    for hit in hits:
        assert cosines[hit.chunk_id] == pytest.approx(hit.score, abs=1e-6)


def test_cosine_similarities_scores_chunks_search_never_returned(built):
    index = built[0]
    returned = {h.chunk_id for h in index.query("database connections maxed out", k=3)}
    other = next(h.chunk_id for h in index.query("sms delivery failing", k=50) if h.chunk_id not in returned)

    cosines = index.cosine_similarities("database connections maxed out", [other])

    assert -1.0 <= cosines[other] <= 1.0


def test_cosine_similarities_of_no_chunks_is_empty(built):
    assert built[0].cosine_similarities("anything", []) == {}
