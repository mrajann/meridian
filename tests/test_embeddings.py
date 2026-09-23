import math
from types import SimpleNamespace

import pytest

from meridian.catalog import load_catalog
from meridian.config import Settings
from meridian.corpus import generate_corpus
from meridian.indexing import Embedder, HashingEmbedder, chunk_budget, chunk_corpus, get_embedder
from meridian.indexing.store import build_filter


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # vectors are unit length


# ------------------------------------------------------- hashing baseline


def test_hashing_embedder_satisfies_the_embedder_interface():
    assert isinstance(HashingEmbedder(), Embedder)


def test_hashing_embedder_is_deterministic_and_unit_length():
    a = HashingEmbedder().embed(["database connections maxed out"])[0]
    b = HashingEmbedder().embed(["database connections maxed out"])[0]

    assert a == b
    assert len(a) == 256
    assert math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-9)


def test_hashing_embedder_scores_shared_vocabulary_above_unrelated_text():
    embed = HashingEmbedder().embed
    query, related, unrelated = embed(
        [
            "postgres database connections maxed out",
            "database connections are maxed out on postgres",
            "sms delivery failing at the twilio provider",
        ]
    )

    assert cosine(query, related) > cosine(query, unrelated)


def test_hashing_token_estimate_grows_with_length():
    embedder = HashingEmbedder()

    assert embedder.count_tokens("one two three four five six") > embedder.count_tokens("one two")


def test_chunk_budget_scales_with_the_embedders_own_limit():
    assert chunk_budget(HashingEmbedder(max_input_tokens=256)) == 192
    assert chunk_budget(HashingEmbedder(max_input_tokens=512)) == 384


def test_factory_builds_the_configured_backend():
    embedder = get_embedder(Settings(embedding_backend="hashing", _env_file=None))

    assert isinstance(embedder, HashingEmbedder)


def test_factory_rejects_an_unknown_backend():
    with pytest.raises(ValueError, match="unknown embedding backend"):
        get_embedder(SimpleNamespace(embedding_backend="nope"))


# ---------------------------------------- real model (needs local-embeddings)


@pytest.fixture(scope="module")
def real_embedder():
    pytest.importorskip("sentence_transformers")
    from meridian.indexing import SentenceTransformerEmbedder

    try:
        return SentenceTransformerEmbedder()
    except OSError:
        pytest.skip("embedding model is not downloaded and the network is unavailable")


def test_sentence_transformer_embedder_reports_its_model_limits(real_embedder):
    assert isinstance(real_embedder, Embedder)
    assert real_embedder.dimension == 384
    assert real_embedder.max_input_tokens == 256


def test_sentence_transformer_vectors_are_unit_length(real_embedder):
    vector = real_embedder.embed(["connection pool exhausted"])[0]

    assert math.isclose(sum(x * x for x in vector), 1.0, rel_tol=1e-4)


def test_sentence_transformer_understands_paraphrase_the_hashing_baseline_cannot(real_embedder):
    query = "connection pool exhausted"
    paraphrase = "database connections maxed out"
    unrelated = "sms messages are not being delivered to customers"

    real = real_embedder.embed([query, paraphrase, unrelated])
    lexical = HashingEmbedder().embed([query, paraphrase, unrelated])

    assert cosine(real[0], real[1]) > cosine(real[0], real[2]) + 0.1
    # No shared words, so the lexical baseline sees the paraphrase as no closer than noise.
    assert cosine(lexical[0], lexical[1]) < 0.2


def test_tokenizer_counts_hyphenated_service_names_as_several_tokens(real_embedder):
    assert real_embedder.count_tokens("postgres-primary") > real_embedder.count_tokens("postgres") + 1


def test_no_chunk_of_the_real_corpus_is_truncated_by_the_model(real_embedder):
    """The guarantee the chunk budget exists to provide: text past the model's
    limit is silently dropped from the embedding, so no chunk may reach it."""
    documents = generate_corpus(load_catalog())
    budget = chunk_budget(real_embedder)

    chunks = chunk_corpus(documents, real_embedder.count_tokens, budget)

    longest = max(real_embedder.count_tokens(c.embed_text) for c in chunks)
    assert longest <= budget < real_embedder.max_input_tokens


def test_semantic_search_is_sane_on_vocabulary_mismatch_cases(real_embedder, tmp_path):
    """A smoke floor, not an evaluation (precision@k / recall@k is increment 5):
    alert text should find its differently-worded runbook among the top 5
    runbooks most of the time. Measured at 24/28 when written; the floor leaves
    room for model/version drift while still catching a broken pipeline."""
    from meridian.indexing import VectorIndex, build_index

    catalog = load_catalog()
    documents = generate_corpus(catalog)
    index = VectorIndex(tmp_path, real_embedder)
    build_index(documents, catalog, real_embedder, index)

    alerts = [
        d for d in documents if d.doc_type == "alert" and d.metadata.get("adversarial_case") == "vocabulary_mismatch"
    ]
    found = 0
    for alert in alerts:
        hits = index.query(alert.body, k=5, where=build_filter(doc_type="runbook"))
        found += any(h.doc_id == alert.metadata["correct_runbook"] for h in hits)

    assert len(alerts) >= 25
    assert found >= 18, f"only {found}/{len(alerts)} vocabulary-mismatch alerts found their runbook in the top 5"
