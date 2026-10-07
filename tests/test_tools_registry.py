import inspect
import json

import pytest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaValidationError

from meridian.tools import TOOL_ORDER, Tool, ToolContext, ToolError, Toolset, registered_tools
from meridian.tools.schema import validate_arguments

GROUND_TRUTH_KEYS = {
    "deploy_causal", "decoy_deploy", "causal", "decoy", "correlated", "correct_runbook", "has_matching_runbook",
    "root_cause_service", "root_cause_category", "adversarial_case", "fragile_service", "stale_reference",
    "affected_services", "onset", "category",
}


def keys_anywhere(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys_anywhere(v)
    elif isinstance(value, list):
        for item in value:
            yield from keys_anywhere(item)


# ---------------------------------------------------------------------- Toolset


def test_a_toolset_exposes_all_eleven_tools_in_order(s_ctx):
    toolset = Toolset(s_ctx)

    assert toolset.names == TOOL_ORDER and [s["name"] for s in toolset.schemas()] == TOOL_ORDER
    assert toolset.schemas() == [t.schema() for t in registered_tools().values()]


def test_bound_functions_have_the_real_signature_without_ctx_and_the_real_docstring(s_ctx):
    toolset = Toolset(s_ctx)

    for name, tool in registered_tools().items():
        bound = toolset.functions[name]
        assert list(inspect.signature(bound).parameters) == list(tool.params)
        assert bound.__doc__ == tool.func.__doc__ and bound.__name__ == name


def test_defaults_survive_in_the_bound_signature(s_ctx):
    sig = inspect.signature(Toolset(s_ctx).functions["get_dependencies"])

    assert sig.parameters["depth"].default == 1 and sig.parameters["name"].default is inspect.Parameter.empty


def test_tools_can_be_called_as_attributes(s_ctx):
    assert Toolset(s_ctx).get_service(name="checkout-api")["name"] == "checkout-api"
    with pytest.raises(AttributeError):
        Toolset(s_ctx).not_a_tool


def test_positional_and_keyword_calls_are_equivalent(s_ctx):
    toolset = Toolset(s_ctx)

    assert toolset.functions["get_dependencies"]("checkout-api", 2) == toolset.functions["get_dependencies"](
        name="checkout-api", depth=2
    )


def test_a_value_given_both_ways_is_a_type_error(s_ctx):
    with pytest.raises(TypeError, match="multiple values"):
        Toolset(s_ctx).functions["get_service"]("checkout-api", name="checkout-api")


def test_too_many_positional_arguments_is_a_type_error(s_ctx):
    with pytest.raises(TypeError, match="at most 1 positional"):
        Toolset(s_ctx).functions["get_service"]("checkout-api", "extra")


def test_bound_calls_validate_exactly_like_a_models_call(s_ctx):
    with pytest.raises(ToolError, match="unknown argument"):
        Toolset(s_ctx).functions["get_service"](name="checkout-api", colour="red")


def test_calling_an_unknown_tool_lists_the_real_ones(s_ctx):
    with pytest.raises(ToolError) as exc:
        Toolset(s_ctx).call("restart_everything", {})

    assert "unknown tool 'restart_everything'" in str(exc.value) and "get_service" in str(exc.value)


# ----------------------------------------------------------- tool_use -> tool_result


def test_a_tool_use_block_becomes_a_tool_result_block(s_ctx):
    block = {"type": "tool_use", "id": "toolu_abc", "name": "get_service", "input": {"name": "checkout-api"}}

    result = Toolset(s_ctx).run_tool_use(block)

    assert set(result) == {"type", "tool_use_id", "content", "is_error"}
    assert result["type"] == "tool_result" and result["tool_use_id"] == "toolu_abc" and result["is_error"] is False
    assert json.loads(result["content"]) == Toolset(s_ctx).get_service(name="checkout-api")
    assert isinstance(result["content"], str)


def test_a_failing_call_becomes_an_error_result_the_model_can_read(s_ctx):
    block = {"type": "tool_use", "id": "toolu_1", "name": "get_service", "input": {"name": "checkout-ap"}}

    result = Toolset(s_ctx).run_tool_use(block)

    assert result["is_error"] is True and result["tool_use_id"] == "toolu_1"
    assert "Did you mean: checkout-api" in json.loads(result["content"])["error"]


@pytest.mark.parametrize("tool_input", [None, {}])
def test_a_call_with_no_input_reports_the_missing_arguments(s_ctx, tool_input):
    block = {"id": "t", "name": "get_service", "input": tool_input}

    result = Toolset(s_ctx).run_tool_use(block)

    assert result["is_error"] is True and "missing required argument 'name'" in json.loads(result["content"])["error"]


def test_a_block_without_an_input_key_is_handled(s_ctx):
    result = Toolset(s_ctx).run_tool_use({"id": "t", "name": "get_service"})

    assert result["is_error"] is True


def test_an_unknown_tool_name_is_an_error_result_not_a_crash(s_ctx):
    result = Toolset(s_ctx).run_tool_use({"id": "t", "name": "nope", "input": {}})

    assert result["is_error"] is True and "unknown tool" in json.loads(result["content"])["error"]


def test_a_bug_in_a_tool_is_not_swallowed_as_a_model_error(s_ctx):
    def broken(ctx, name: str) -> dict:
        raise RuntimeError("a real bug")

    template = registered_tools()["get_service"]
    tools = {"get_service": Tool("get_service", broken, template.description, template.params)}

    with pytest.raises(RuntimeError, match="a real bug"):
        Toolset(s_ctx, tools).run_tool_use({"id": "t", "name": "get_service", "input": {"name": "checkout-api"}})


# ------------------------------------------------------------------ output sanity


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_every_tool_returns_a_json_serializable_dict(ctx_for, find_scenario, name, valid_args):
    sc = find_scenario()
    result = Toolset(ctx_for(sc.incident_id)).call(name, valid_args(sc)[name])

    assert isinstance(result, dict) and json.loads(json.dumps(result)) == result


def test_no_ground_truth_leaks_out_of_any_tool_across_many_incidents(s_scenarios, ctx_for, valid_args):
    checked = 0
    for incident_id in sorted(s_scenarios)[:: max(1, len(s_scenarios) // 12)]:
        sc = s_scenarios[incident_id]
        toolset = Toolset(ctx_for(incident_id))
        for name, args in valid_args(sc).items():
            leaked = GROUND_TRUTH_KEYS & set(keys_anywhere(toolset.call(name, args)))
            assert not leaked, f"{name} leaked {leaked} for {incident_id}"
            checked += 1

    assert checked >= 11 * 10


def test_read_only_tools_never_touch_the_pager(ctx_for, find_scenario, valid_args):
    sc = find_scenario()
    ctx = ctx_for(sc.incident_id)
    toolset = Toolset(ctx)

    for name, args in valid_args(sc).items():
        if name != "page_oncall":
            toolset.call(name, args)

    assert ctx.pager.records == []


def test_read_only_tools_are_repeatable(ctx_for, find_scenario, valid_args):
    sc = find_scenario()
    toolset = Toolset(ctx_for(sc.incident_id))

    for name, args in valid_args(sc).items():
        if name != "page_oncall":
            assert toolset.call(name, args) == toolset.call(name, args), name


# --------------------------------------------------------------------- the context


def test_a_context_without_an_incident_hides_nothing(s_ctx):
    assert s_ctx.scenario is None and s_ctx.excluded_doc_ids == frozenset()


def test_with_scenario_binds_the_incident_telemetry_and_a_fresh_pager(s_ctx, s_scenarios):
    sc = next(iter(s_scenarios.values()))

    ctx = s_ctx.with_scenario(sc)

    assert ctx.scenario is sc and ctx.now == sc.now and ctx.excluded_doc_ids == sc.excluded_doc_ids
    assert ctx.retriever is s_ctx.retriever and ctx.pager is not s_ctx.pager and isinstance(ctx, ToolContext)


# ----------------------------------------------- the published schemas are real JSON Schema

SCHEMA_CASES = {
    "search_runbooks": ({"query": "latency", "k": 5}, [{"k": 5}, {"query": "latency", "k": 0}, {"query": "latency", "k": 11}, {"query": "ab"}, {"query": "latency", "extra": 1}]),
    "search_postmortems": ({"query": "latency"}, [{}, {"query": "latency", "k": 99}]),
    "find_similar_incidents": ({"description": "latency"}, [{"query": "latency"}, {"description": "x" * 501}]),
    "get_service": ({"name": "x"}, [{}, {"name": ""}, {"name": "x", "depth": 1}]),
    "get_dependencies": ({"name": "x", "depth": 3}, [{"name": "x", "depth": 0}, {"name": "x", "depth": 11}]),
    "get_dependents": ({"name": "x", "depth": 3}, [{"depth": 3}, {"name": "x", "depth": 11}]),
    "query_metrics": ({"service": "x", "metric": "error_rate", "window": "15m"}, [{"service": "x", "metric": "vibes"}, {"service": "x", "metric": "error_rate", "window": "2w"}, {"metric": "error_rate"}]),
    "get_deploy_history": ({"service": "x", "window": "7d"}, [{"service": "x", "window": "forever"}, {"window": "7d"}]),
    "compute_error_budget": ({"service": "x", "slo_target": 99.9, "window_days": 28}, [{"service": "x", "slo_target": 0.999}, {"service": "x", "slo_target": 100}, {"service": "x", "window_days": 6}, {"service": "x", "window_days": 91}]),
    "get_oncall": ({"team": "x"}, [{}, {"team": ""}]),
    "page_oncall": ({"team": "x", "severity": "SEV1", "message": "a message long enough to pass"}, [{"team": "x", "severity": "SEV9", "message": "a message long enough to pass"}, {"team": "x", "severity": "SEV1", "message": "short"}, {"team": "x", "severity": "SEV1"}]),
}


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_each_input_schema_is_valid_json_schema(name):
    Draft202012Validator.check_schema(registered_tools()[name].schema()["input_schema"])


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_the_published_schema_and_the_runtime_validator_agree(name):
    """What the model is told it may send (the schema) must be what the
    dispatcher actually accepts: any input the schema allows must validate,
    and any it forbids must be rejected."""
    tool = registered_tools()[name]
    validator = Draft202012Validator(tool.schema()["input_schema"])
    valid, invalid_cases = SCHEMA_CASES[name]

    assert not list(validator.iter_errors(valid))
    validate_arguments(name, tool.params, dict(valid))
    for bad in invalid_cases:
        assert list(validator.iter_errors(bad)), f"schema accepted {bad}"
        with pytest.raises(ToolError):
            validate_arguments(name, tool.params, dict(bad))


def test_every_tool_is_covered_by_the_schema_agreement_cases():
    assert set(SCHEMA_CASES) == set(TOOL_ORDER)
