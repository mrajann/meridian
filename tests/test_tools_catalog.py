import json

import pytest

from meridian.tools import Toolset, ToolError


def call(ctx, name, /, **kwargs):
    return Toolset(ctx).functions[name](**kwargs)


# ------------------------------------------------------------------- get_service


def test_get_service_matches_the_spec_example_for_checkout_api(s_ctx):
    result = call(s_ctx, "get_service", name="checkout-api")

    assert result["tier"] == 1 and result["owner"] == "payments-platform"
    assert result["oncall_rotation"] == "payments-oncall"
    assert result["depends_on"] == ["auth-service", "postgres-primary", "stripe-gateway", "inventory-service", "pricing-engine"]
    assert set(result["depended_on_by"]) == {"web-frontend", "mobile-api"}
    assert result["slo"] == {"availability_percent": 99.95, "latency_p99_ms": 400}
    assert result["runbooks"] == ["checkout-5xx", "checkout-latency", "checkout-stripe-timeout"]
    assert result["blast_radius"] == "All revenue. Complete outage means no orders can be placed."
    assert result["business_hours_only"] is False and result["external"] is False


@pytest.mark.parametrize("name", ["checkout-api", "postgres-primary", "stripe-gateway", "ci-pipeline", "web-frontend"])
def test_get_service_reports_every_catalog_field(s_ctx, s_catalog, name):
    entry, result = s_catalog[name], call(s_ctx, "get_service", name=name)

    assert result["name"] == entry.name and result["tier"] == entry.tier and result["owner"] == entry.owner
    assert result["description"] == entry.description and result["oncall_rotation"] == entry.oncall_rotation
    assert result["depends_on"] == entry.depends_on and result["depended_on_by"] == entry.depended_on_by
    assert result["business_hours_only"] == entry.business_hours_only


def test_every_service_in_the_catalog_can_be_looked_up_and_serialized(s_ctx, s_catalog):
    for name in s_catalog:
        json.dumps(call(s_ctx, "get_service", name=name))


def test_third_party_services_are_marked_external_with_no_rotation(s_ctx):
    result = call(s_ctx, "get_service", name="stripe-gateway")

    assert result["external"] is True and result["tier"] == "external" and result["oncall_rotation"] is None


def test_get_service_ignores_case_and_surrounding_whitespace(s_ctx):
    assert call(s_ctx, "get_service", name="  Checkout-API ")["name"] == "checkout-api"


def test_an_unknown_service_gets_near_matches_and_the_decommissioned_hint(s_ctx):
    with pytest.raises(ToolError) as exc:
        call(s_ctx, "get_service", name="checkout-monolith-v1")

    message = str(exc.value)
    assert "No service named 'checkout-monolith-v1'" in message
    assert "Did you mean: checkout-api" in message
    assert "decommissioned" in message


def test_a_name_with_no_near_matches_still_explains_itself(s_ctx):
    with pytest.raises(ToolError) as exc:
        call(s_ctx, "get_service", name="zzzzzzzzzz")

    assert "Did you mean" not in str(exc.value) and "decommissioned" in str(exc.value)


def test_an_empty_name_is_rejected_by_validation(s_ctx):
    with pytest.raises(ToolError, match="name"):
        call(s_ctx, "get_service", name="")


# ----------------------------------------------------------------- dependencies


def test_dependencies_default_to_direct_ones(s_ctx, s_catalog):
    result = call(s_ctx, "get_dependencies", name="checkout-api")

    assert result["depth"] == 1 and result["direction"] == "dependencies"
    assert {s["name"] for s in result["services"]} == set(s_catalog["checkout-api"].depends_on)
    assert {s["hops"] for s in result["services"]} == {1} and result["count"] == 5


def test_a_greater_depth_follows_the_chain_and_reports_hop_distance(s_ctx):
    result = call(s_ctx, "get_dependencies", name="orders-service", depth=2)
    hops = {s["name"]: s["hops"] for s in result["services"]}

    assert hops["postgres-primary"] == 1 and hops["redis-cache"] == 2  # via inventory-service
    assert hops["kafka-broker"] == 2  # via notification-service
    assert result["by_hop"]["1"] and result["by_hop"]["2"]


def test_results_are_ordered_nearest_first(s_ctx):
    services = call(s_ctx, "get_dependents", name="postgres-primary", depth=10)["services"]

    assert [s["hops"] for s in services] == sorted(s["hops"] for s in services)


def test_by_hop_groups_exactly_the_listed_services(s_ctx):
    result = call(s_ctx, "get_dependents", name="postgres-primary", depth=10)

    assert sum(len(v) for v in result["by_hop"].values()) == result["count"]
    for hop, names in result["by_hop"].items():
        assert {s["hops"] for s in result["services"] if s["name"] in names} == {int(hop)}


def test_each_listed_service_carries_tier_owner_and_external_flag(s_ctx):
    services = call(s_ctx, "get_dependencies", name="checkout-api")["services"]
    stripe = next(s for s in services if s["name"] == "stripe-gateway")

    assert stripe["external"] is True and stripe["tier"] == "external"
    assert next(s for s in services if s["name"] == "auth-service")["owner"] == "identity-platform"


def test_a_service_with_no_dependencies_returns_an_empty_list(s_ctx):
    result = call(s_ctx, "get_dependencies", name="postgres-primary", depth=10)

    assert result["services"] == [] and result["count"] == 0 and result["by_hop"] == {}


@pytest.mark.parametrize("tool", ["get_dependencies", "get_dependents"])
@pytest.mark.parametrize("depth", [0, 11, -1])
def test_depth_is_bounded(s_ctx, tool, depth):
    with pytest.raises(ToolError, match="depth"):
        call(s_ctx, tool, name="checkout-api", depth=depth)


@pytest.mark.parametrize("tool", ["get_dependencies", "get_dependents"])
def test_graph_tools_reject_unknown_services_with_suggestions(s_ctx, tool):
    with pytest.raises(ToolError, match="Did you mean: checkout-api"):
        call(s_ctx, tool, name="checkout-ap")


@pytest.mark.parametrize("tool", ["get_dependencies", "get_dependents"])
def test_graph_tools_use_the_canonical_name(s_ctx, tool):
    assert call(s_ctx, tool, name="CHECKOUT-API")["service"] == "checkout-api"


# ------------------------------------------------------------------- dependents


def test_dependents_of_postgres_primary_at_full_depth_is_the_whole_cascade(s_ctx):
    result = call(s_ctx, "get_dependents", name="postgres-primary", depth=10)
    names = {s["name"] for s in result["services"]}

    assert names == s_ctx.graph.dependents("postgres-primary") and result["count"] == 24
    assert {"checkout-api", "web-frontend", "mobile-api", "recommendation-engine"} <= names
    assert not names & {"stripe-gateway", "secrets-manager", "notification-service"}  # not downstream of it


def test_dependents_hop_distances_reflect_the_chain(s_ctx):
    hops = {s["name"]: s["hops"] for s in call(s_ctx, "get_dependents", name="postgres-primary", depth=10)["services"]}

    assert hops["checkout-api"] == 1 and hops["web-frontend"] == 2


def test_depth_one_dependents_are_exactly_the_direct_callers(s_ctx, s_catalog):
    result = call(s_ctx, "get_dependents", name="postgres-primary")

    assert {s["name"] for s in result["services"]} == set(s_catalog["postgres-primary"].depended_on_by)


def test_a_leaf_consumer_has_no_dependents(s_ctx):
    assert call(s_ctx, "get_dependents", name="web-frontend", depth=10)["count"] == 0


def test_the_two_directions_are_exact_inverses_at_depth_one(s_ctx, s_catalog):
    for a in s_catalog:
        for b in {s["name"] for s in call(s_ctx, "get_dependencies", name=a)["services"]}:
            assert a in {s["name"] for s in call(s_ctx, "get_dependents", name=b)["services"]}, (a, b)
