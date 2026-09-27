import pytest

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.indexing import HashingEmbedder, VectorIndex, build_filter, build_index
from meridian.retrieval import Retriever
from meridian.retrieval.keyword import BM25Index, ScoredId, matches_where, tokenize
from meridian.retrieval.retriever import (
    DEFAULT_FUSION,
    DEFAULT_KEYWORD_WEIGHT,
    DEFAULT_VECTOR_WEIGHT,
    _minmax_normalize,
    _reciprocal_rank_fusion,
    _weighted_sum_fusion,
)


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
    fused = _reciprocal_rank_fusion([(["a", "b", "c"], 1.0), (["b", "a", "c"], 1.0)])

    assert fused["a"] == fused["b"]  # rank 1+2 vs rank 2+1, symmetric
    assert fused["a"] > fused["c"]


def test_rrf_credits_an_item_missing_from_one_list():
    only_in_one = _reciprocal_rank_fusion([(["a"], 1.0), ([], 1.0)])
    in_both = _reciprocal_rank_fusion([(["a"], 1.0), (["a"], 1.0)])

    assert 0 < only_in_one["a"] < in_both["a"]


def test_rrf_weight_scales_a_lists_contribution():
    equal = _reciprocal_rank_fusion([(["a"], 1.0), (["b"], 1.0)])
    weighted = _reciprocal_rank_fusion([(["a"], 3.0), (["b"], 1.0)])

    assert equal["a"] == equal["b"]
    assert weighted["a"] > weighted["b"]
    assert weighted["a"] == pytest.approx(3.0 * equal["a"])


# ------------------------------------------------------- weighted-sum fusion


def test_minmax_normalize_maps_the_range_to_zero_one():
    normalized = _minmax_normalize([ScoredId("a", 10.0), ScoredId("b", 20.0), ScoredId("c", 30.0)])

    assert normalized == {"a": 0.0, "b": 0.5, "c": 1.0}


def test_minmax_normalize_of_tied_scores_is_all_ones_not_a_division_by_zero():
    assert _minmax_normalize([ScoredId("a", 5.0), ScoredId("b", 5.0)]) == {"a": 1.0, "b": 1.0}


def test_minmax_normalize_of_empty_input_is_empty():
    assert _minmax_normalize([]) == {}


def test_weighted_sum_fusion_lets_a_confident_number_one_outrank_a_weak_ones_rank():
    from meridian.indexing.store import Hit

    # keyword ranks "b" 1st, vector ranks "a" 1st but only weakly (barely
    # above the rest) -- with normalization this shows up as a small vector
    # score for "a", so a strong keyword signal for "b" can still win.
    vector_hits = [
        Hit(chunk_id="a", text="", score=0.501, metadata={}),
        Hit(chunk_id="b", text="", score=0.500, metadata={}),
        Hit(chunk_id="c", text="", score=0.499, metadata={}),
    ]
    keyword_scored = [ScoredId("b", 10.0), ScoredId("c", 1.0), ScoredId("a", 0.5)]

    fused = _weighted_sum_fusion(vector_hits, keyword_scored, vector_weight=1.0, keyword_weight=1.0)

    assert max(fused, key=fused.get) == "b"


def test_weighted_sum_fusion_weight_zero_ignores_that_side():
    from meridian.indexing.store import Hit

    vector_hits = [Hit(chunk_id="a", text="", score=0.9, metadata={})]
    keyword_scored = [ScoredId("b", 100.0)]

    fused = _weighted_sum_fusion(vector_hits, keyword_scored, vector_weight=1.0, keyword_weight=0.0)

    assert fused == {"a": 1.0, "b": 0.0}


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


def test_default_fusion_is_weighted_sum_favoring_vector():
    assert DEFAULT_FUSION == "weighted_sum"
    assert DEFAULT_VECTOR_WEIGHT > DEFAULT_KEYWORD_WEIGHT


def test_hybrid_search_accepts_an_explicit_fusion_and_weights(retriever):
    default = retriever.search("connection pool exhausted", k=5, mode="hybrid")
    rrf = retriever.search("connection pool exhausted", k=5, mode="hybrid", fusion="rrf")
    keyword_only = retriever.search(
        "connection pool exhausted", k=5, mode="hybrid", vector_weight=0.0, keyword_weight=1.0
    )

    assert [h.chunk_id for h in default] != [h.chunk_id for h in rrf] or default[0].score != rrf[0].score
    assert [h.chunk_id for h in keyword_only] == [
        h.chunk_id for h in retriever.search("connection pool exhausted", k=5, mode="keyword")
    ]


def test_hybrid_unknown_fusion_raises(retriever):
    with pytest.raises(ValueError, match="unknown fusion algorithm"):
        retriever.search("x", mode="hybrid", fusion="nonexistent")


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
