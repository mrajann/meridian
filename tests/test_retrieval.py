import pytest

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.indexing import HashingEmbedder, VectorIndex, build_filter, build_index
from meridian.retrieval import Retriever
from meridian.retrieval.keyword import BM25Index, matches_where, tokenize
from meridian.retrieval.retriever import _reciprocal_rank_fusion


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


# --------------------------------------------------------------- tokenize


def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("Connection Pool Exhausted!") == ["connection", "pool", "exhausted"]


def test_tokenize_splits_hyphenated_service_names():
    assert tokenize("postgres-primary") == ["postgres", "primary"]


# ---------------------------------------------------------------- BM25


def test_bm25_ranks_more_matching_terms_higher():
    index = BM25Index(
        ids=["a", "b", "c"],
        texts=["connection pool exhausted on the database", "database is fine", "unrelated weather report"],
        metadatas=[{}, {}, {}],
    )

    results = index.search("connection pool exhausted", k=3)

    assert [r.id for r in results][:1] == ["a"]
    assert all(r.score > 0 for r in results if r.id != "c")


def test_bm25_query_with_no_known_terms_returns_nothing():
    index = BM25Index(ids=["a"], texts=["connection pool exhausted"], metadatas=[{}])

    assert index.search("completely unrelated wording", k=5) == []


def test_bm25_respects_where_filter():
    index = BM25Index(
        ids=["a", "b"],
        texts=["connection pool exhausted", "connection pool exhausted"],
        metadatas=[{"doc_type": "runbook"}, {"doc_type": "alert"}],
    )

    results = index.search("connection pool exhausted", k=5, where={"doc_type": "runbook"})

    assert [r.id for r in results] == ["a"]


# ------------------------------------------------------------ matches_where


def test_matches_where_none_matches_everything():
    assert matches_where({"doc_type": "runbook"}, None)


def test_matches_where_equality():
    assert matches_where({"tier": "1"}, {"tier": "1"})
    assert not matches_where({"tier": "2"}, {"tier": "1"})


def test_matches_where_in():
    assert matches_where({"tier": "2"}, {"tier": {"$in": ["1", "2"]}})
    assert not matches_where({"tier": "3"}, {"tier": {"$in": ["1", "2"]}})


def test_matches_where_contains_on_list_field():
    assert matches_where({"services": ["a", "b"]}, {"services": {"$contains": "a"}})
    assert not matches_where({"services": ["a", "b"]}, {"services": {"$contains": "z"}})
    assert not matches_where({}, {"services": {"$contains": "a"}})


def test_matches_where_and():
    where = {"$and": [{"doc_type": "runbook"}, {"tier": "1"}]}

    assert matches_where({"doc_type": "runbook", "tier": "1"}, where)
    assert not matches_where({"doc_type": "runbook", "tier": "2"}, where)


# --------------------------------------------------------------------- RRF


def test_rrf_favors_items_ranked_highly_in_both_lists():
    fused = _reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "c"]])

    assert fused["a"] == fused["b"]  # rank 1+2 vs rank 2+1, symmetric
    assert fused["a"] > fused["c"]


def test_rrf_credits_an_item_missing_from_one_list():
    only_in_one = _reciprocal_rank_fusion([["a"], []])
    in_both = _reciprocal_rank_fusion([["a"], ["a"]])

    assert 0 < only_in_one["a"] < in_both["a"]


# -------------------------------------------------------------- Retriever


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid"])
def test_each_mode_returns_k_hits_in_descending_score_order(retriever, mode):
    hits = retriever.search("connection pool exhausted", k=6, mode=mode)

    assert len(hits) == 6
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid"])
def test_each_mode_respects_the_where_filter(retriever, mode):
    hits = retriever.search("incident", k=50, where=build_filter(doc_type="runbook"), mode=mode)

    assert hits
    assert {h.metadata["doc_type"] for h in hits} == {"runbook"}


def test_unknown_mode_raises(retriever):
    with pytest.raises(ValueError, match="unknown retrieval mode"):
        retriever.search("x", mode="fuzzy")


def test_keyword_search_sees_title_and_service_context_like_vector_search_does(retriever, documents):
    # The stored chunk text alone often doesn't repeat the service name (see
    # meridian.indexing.chunking headers); keyword search reconstructs that
    # context from metadata so it isn't handicapped relative to vector search,
    # whose embeddings include the header.
    runbook = next(d for d in documents if d.doc_type == "runbook" and "checkout-api" in d.services)

    hits = retriever.search(runbook.services[0], k=50, where=build_filter(doc_type="runbook"), mode="keyword")

    assert runbook.doc_id in {h.doc_id for h in hits}


def test_keyword_index_is_built_once_and_cached(retriever):
    retriever.search("connection pool", mode="keyword")
    cached = retriever._bm25

    retriever.search("something else", mode="keyword")

    assert retriever._bm25 is cached


def test_hybrid_result_can_include_a_document_only_one_side_found(retriever, documents):
    # A cascade alert lists several services in its own body -- likely to
    # rank higher under BM25's exact-term matching than under semantic
    # similarity to a generic-phrased root-cause runbook.
    cascade = next(d for d in documents if d.metadata.get("adversarial_case") == "cascading_failure")

    vector_ids = {h.doc_id for h in retriever.search(cascade.body, k=10, mode="vector")}
    keyword_ids = {h.doc_id for h in retriever.search(cascade.body, k=10, mode="keyword")}
    hybrid_ids = {h.doc_id for h in retriever.search(cascade.body, k=10, mode="hybrid")}

    assert hybrid_ids - vector_ids or hybrid_ids - keyword_ids
