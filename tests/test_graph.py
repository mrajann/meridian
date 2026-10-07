import pytest

from meridian.catalog import ServiceEntry, load_catalog
from meridian.graph import DependencyGraph


def _entry(name: str, depends_on: list[str], depended_on_by: list[str]) -> ServiceEntry:
    return ServiceEntry.model_validate(
        {
            "name": name,
            "tier": 1,
            "owner": "test-team",
            "description": "A test service.",
            "depends_on": depends_on,
            "depended_on_by": depended_on_by,
            "slo": {"availability": 99.9, "latency_p99_ms": 200},
            "runbooks": [],
            "blast_radius": "Minimal.",
        }
    )


@pytest.fixture
def real_catalog():
    return load_catalog()


@pytest.fixture
def cyclic_catalog():
    # a -> b -> c -> a, a cycle with no acyclic component to fall back on.
    return {
        "a": _entry("a", depends_on=["b"], depended_on_by=["c"]),
        "b": _entry("b", depends_on=["c"], depended_on_by=["a"]),
        "c": _entry("c", depends_on=["a"], depended_on_by=["b"]),
    }


def test_dependents_of_postgres_primary_is_full_transitive_set(real_catalog):
    graph = DependencyGraph(real_catalog)

    dependents = graph.dependents("postgres-primary")

    # Direct dependents.
    assert "checkout-api" in dependents
    assert "auth-service" in dependents
    # Transitive: web-frontend depends on checkout-api, which depends on
    # postgres-primary -- two hops away, and exactly what cascade detection
    # needs to catch rather than reporting web-frontend as a separate incident.
    assert "web-frontend" in dependents
    assert "mobile-api" in dependents
    # Three hops: recommendation-engine -> llm-gateway -> feature-flags is a
    # different chain that never touches postgres-primary, but
    # recommendation-engine -> analytics-api -> warehouse-etl -> postgres-replica
    # -> postgres-primary does.
    assert "recommendation-engine" in dependents
    # Services with no path to postgres-primary must not appear.
    assert "stripe-gateway" not in dependents
    assert "secrets-manager" not in dependents
    assert "postgres-primary" not in dependents


def test_dependencies_and_dependents_are_inverse_views(real_catalog):
    graph = DependencyGraph(real_catalog)

    for name in real_catalog:
        for dep in graph.dependencies(name, depth=1):
            assert name in graph.dependents(dep, depth=1)


def test_depth_limits_traversal(real_catalog):
    graph = DependencyGraph(real_catalog)

    direct = graph.dependents("postgres-primary", depth=1)
    full = graph.dependents("postgres-primary")

    assert direct.issubset(full)
    assert direct < full  # depth=1 must be a strict subset of the full cascade
    assert "checkout-api" in direct
    assert "web-frontend" not in direct  # two hops away, excluded at depth=1


def test_unknown_service_raises(real_catalog):
    graph = DependencyGraph(real_catalog)

    with pytest.raises(KeyError):
        graph.dependents("does-not-exist")


def test_circular_dependency_does_not_infinite_loop(cyclic_catalog):
    graph = DependencyGraph(cyclic_catalog)

    dependents = graph.dependents("a")
    dependencies = graph.dependencies("a")

    assert dependents == {"b", "c"}
    assert dependencies == {"b", "c"}


def test_circular_dependency_respects_depth(cyclic_catalog):
    graph = DependencyGraph(cyclic_catalog)

    assert graph.dependencies("a", depth=1) == {"b"}
    assert graph.dependencies("a", depth=2) == {"b", "c"}


# --- hop distances ---


def test_dependents_with_hops_reports_shortest_distance(real_catalog):
    graph = DependencyGraph(real_catalog)

    hops = graph.dependents_with_hops("postgres-primary")

    assert hops["checkout-api"] == 1  # depends on postgres-primary directly
    assert hops["web-frontend"] == 2  # via checkout-api
    assert set(hops) == graph.dependents("postgres-primary")


def test_hops_respect_the_depth_limit(real_catalog):
    graph = DependencyGraph(real_catalog)

    hops = graph.dependents_with_hops("postgres-primary", depth=1)

    assert set(hops.values()) == {1}
    assert "web-frontend" not in hops


def test_a_service_reachable_by_two_paths_gets_its_shortest_distance(cyclic_catalog):
    hops = DependencyGraph(cyclic_catalog).dependencies_with_hops("a")

    assert hops == {"b": 1, "c": 2}  # never revisited, never "a" itself, despite the cycle


def test_dependencies_with_hops_unknown_service_raises(real_catalog):
    with pytest.raises(KeyError):
        DependencyGraph(real_catalog).dependencies_with_hops("nope")
