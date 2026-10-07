"""Session-scoped fixtures shared by the tool-layer tests: the catalog, the
generated corpus, a hashing-embedder index built once, and every incident's
synthetic scenario. (Older test modules define their own module-scoped
fixtures and are unaffected.)"""

import pytest

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.indexing import HashingEmbedder, VectorIndex, build_index
from meridian.retrieval import Retriever
from meridian.telemetry import build_scenarios
from meridian.tools import build_context


@pytest.fixture(scope="session")
def s_catalog():
    return load_catalog()


@pytest.fixture(scope="session")
def s_documents(s_catalog):
    return generate_corpus(s_catalog)


@pytest.fixture(scope="session")
def s_retriever(tmp_path_factory, s_catalog, s_documents):
    embedder = HashingEmbedder()
    index = VectorIndex(tmp_path_factory.mktemp("tools_chroma"), embedder)
    build_index(s_documents, s_catalog, embedder, index)
    return Retriever(index)


@pytest.fixture(scope="session")
def s_scenarios(s_documents, s_catalog):
    return build_scenarios(s_documents, s_catalog)


@pytest.fixture(scope="session")
def s_ctx(s_catalog, s_retriever):
    """A context with no active incident: a healthy platform at the default 'now'."""
    return build_context(s_catalog, s_retriever)


@pytest.fixture
def ctx_for(s_ctx, s_scenarios):
    """ctx_for(incident_id) -> a fresh context investigating that incident."""

    def make(incident_id: str):
        return s_ctx.with_scenario(s_scenarios[incident_id])

    return make


@pytest.fixture
def find_scenario(s_scenarios):
    """find_scenario(**filters) -> first Scenario whose attributes match, in
    incident-id order so the pick is stable."""

    def find(predicate=None, **attrs):
        for incident_id in sorted(s_scenarios):
            sc = s_scenarios[incident_id]
            if all(getattr(sc, k) == v for k, v in attrs.items()) and (predicate is None or predicate(sc)):
                return sc
        raise LookupError(f"no scenario matches {attrs}")

    return find
