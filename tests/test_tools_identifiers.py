"""Catalog identifiers (service and team names) are normalized once, by their
type, at the single validation step every tool call passes through -- not
remembered tool by tool. These tests enumerate the live registry, so a tool
added later is covered without anyone touching this file.

Three layers:

1. every entity parameter normalizes in validation (needs no sample data);
2. every tool with an entity parameter returns *identical output* for
   mixed-case, padded input (needs one sample call per tool, and fails loudly
   if a tool has none);
3. registration refuses a string parameter whose kind is undeclared, so the
   normalization cannot be skipped by writing `service: str`.
"""

import typing
from typing import Annotated

import pytest
from pydantic import Field, ValidationError

from meridian.tools import TOOL_ORDER, Toolset, ToolDefinitionError, ToolError, registered_tools
from meridian.tools import registry as registry_module
from meridian.tools.catalog_tools import require_service
from meridian.tools.schema import _string_leaves, extract_params, parse_docstring
from meridian.tools.types import (
    ENTITY_PARAMETER_NAMES,
    CatalogEntity,
    Message,
    SearchText,
    ServiceName,
    TeamName,
    Verbatim,
    Window,
    normalize_identifier,
)

LONG_DOC = "x" * 250


def entity_params(tool):
    return [
        p
        for p in tool.params.values()
        if any(isinstance(m, CatalogEntity) for markers in _string_leaves(p.annotation) for m in markers)
    ]


ENTITY_TOOLS = [name for name, tool in registered_tools().items() if entity_params(tool)]

MESSY = {
    "upper": str.upper,
    "title": str.title,
    "swapcase": str.swapcase,
    "padded": lambda v: f"  {v}  ",
    "padded-mixed": lambda v: f"\t{v.title()} \n",
}


def doc(*params):
    args = "\n".join(f"    {p}: a parameter." for p in params)
    return f"{LONG_DOC}\n\nDo not use this.\n\nArgs:\n{args}\n"


# ----------------------------------------------- 1. validation-level, no sample data


def test_the_known_entity_parameters_are_found_so_the_sweeps_below_are_not_vacuous():
    found = {(name, p.name) for name, tool in registered_tools().items() for p in entity_params(tool)}

    assert found >= {
        ("get_service", "name"), ("get_dependencies", "name"), ("get_dependents", "name"),
        ("query_metrics", "service"), ("get_deploy_history", "service"), ("compute_error_budget", "service"),
        ("get_oncall", "team"), ("page_oncall", "team"),
    }


@pytest.mark.parametrize("variant", MESSY.values(), ids=MESSY.keys())
def test_every_entity_parameter_of_every_tool_normalizes_during_validation(variant):
    checked = 0
    for name, tool in registered_tools().items():
        for param in entity_params(tool):
            canonical = "checkout-api"
            assert param.adapter.validate_python(variant(canonical)) == canonical, f"{name}.{param.name}"
            checked += 1

    assert checked >= 8


def test_every_string_parameter_of_every_tool_declares_its_kind():
    for name, tool in registered_tools().items():
        for param in tool.params.values():
            for markers in _string_leaves(param.annotation):
                assert any(isinstance(m, (CatalogEntity, Verbatim)) for m in markers), f"{name}.{param.name}"


def test_parameters_named_like_entities_are_always_declared_as_entities():
    for name, tool in registered_tools().items():
        for param in tool.params.values():
            if param.name in ENTITY_PARAMETER_NAMES:
                assert param in entity_params(tool), f"{name}.{param.name}"


def test_free_text_parameters_are_left_exactly_as_given():
    queries = registered_tools()["search_runbooks"].params["query"]

    assert queries.adapter.validate_python("  Connection POOL exhausted  ") == "  Connection POOL exhausted  "


# --------------------------------------- 2. end to end: identical output, every tool


def test_every_registered_tool_has_a_sample_call(valid_args, find_scenario):
    samples = valid_args(find_scenario())

    missing = set(registered_tools()) - set(samples)
    assert not missing, f"add a sample call to the valid_args fixture in tests/conftest.py for: {sorted(missing)}"


@pytest.mark.parametrize("tool_name", ENTITY_TOOLS)
@pytest.mark.parametrize("variant_name", list(MESSY))
def test_mixed_case_and_padded_names_produce_identical_output(
    tool_name, variant_name, valid_args, find_scenario, ctx_for
):
    scenario = find_scenario()
    sample = valid_args(scenario)[tool_name]
    tool = registered_tools()[tool_name]
    variant = MESSY[variant_name]

    def run(arguments):  # a fresh context each time: page_oncall mutates the pager
        return Toolset(ctx_for(scenario.incident_id)).call(tool_name, arguments)

    baseline = run(sample)
    for param in entity_params(tool):
        original = sample[param.name]
        messy = {**sample, param.name: variant(original)}
        assert messy[param.name] != original, "the variant must actually differ or this proves nothing"
        assert run(messy) == baseline, f"{tool_name}({param.name}={messy[param.name]!r})"

    everything = {**sample, **{p.name: variant(sample[p.name]) for p in entity_params(tool)}}
    assert run(everything) == baseline


def test_a_model_sending_messy_names_through_the_anthropic_path_succeeds(s_ctx):
    block = {"id": "t1", "name": "get_dependents", "input": {"name": "  POSTGRES-Primary ", "depth": 1}}

    result = Toolset(s_ctx).run_tool_use(block)

    assert result["is_error"] is False and '"service": "postgres-primary"' in result["content"]


def test_a_not_found_message_names_the_normalized_spelling_and_suggests_matches(s_ctx):
    with pytest.raises(ToolError) as exc:
        Toolset(s_ctx).call("get_service", {"name": "  Checkout-AP "})

    assert "No service named 'checkout-ap'" in str(exc.value) and "Did you mean: checkout-api" in str(exc.value)


# ------------------------------------------------ the types themselves


def test_normalize_identifier_strips_folds_case_and_is_idempotent():
    assert normalize_identifier("  CheCkout-API\n") == "checkout-api"
    assert normalize_identifier(normalize_identifier(" A ")) == "a"


@pytest.mark.parametrize("value", [5, None, ["a"], {"a": 1}, 1.5])
def test_normalize_identifier_passes_non_strings_through_for_validation_to_report(value):
    assert normalize_identifier(value) is value


@pytest.mark.parametrize("kind", [ServiceName, TeamName])
def test_whitespace_only_names_are_rejected_because_the_bounds_apply_after_normalizing(kind):
    from pydantic import TypeAdapter

    with pytest.raises(ValidationError):
        TypeAdapter(kind).validate_python("   ")


@pytest.mark.parametrize("kind", [ServiceName, TeamName])
def test_non_string_names_are_rejected_as_a_type_error(kind):
    from pydantic import TypeAdapter

    with pytest.raises(ValidationError, match="valid string"):
        TypeAdapter(kind).validate_python(5)


def test_the_length_limit_applies_to_the_normalized_value():
    from pydantic import TypeAdapter

    adapter = TypeAdapter(ServiceName)

    assert adapter.validate_python(" " + "a" * 100 + " ") == "a" * 100
    with pytest.raises(ValidationError):
        adapter.validate_python("a" * 101)


def test_normalization_does_not_change_the_published_schema():
    from pydantic import TypeAdapter

    assert TypeAdapter(ServiceName).json_schema() == {"type": "string", "minLength": 1, "maxLength": 100}


def test_require_service_still_normalizes_for_callers_holding_a_raw_string(s_ctx):
    assert require_service(s_ctx, "  CHECKOUT-API ").name == "checkout-api"


# -------------------------------------------------- 3. the registration guard


@pytest.fixture
def isolated_registry(monkeypatch):
    monkeypatch.setattr(registry_module, "_REGISTRY", {})
    return registry_module


def extract(func):
    return extract_params(func, parse_docstring(func.__doc__))


def test_a_bare_string_parameter_is_rejected_with_instructions():
    def forgetful(ctx, service: str) -> dict:
        pass

    forgetful.__doc__ = doc("service")

    with pytest.raises(ToolDefinitionError) as exc:
        extract(forgetful)

    message = str(exc.value)
    assert "`service` is a plain string" in message and "ServiceName" in message and "Verbatim" in message


@pytest.mark.parametrize(
    "annotation",
    [str, str | None, list[str], dict[str, str], Annotated[str, Field(min_length=1)], Annotated[list[str], Verbatim()]],
    ids=["bare", "optional", "list", "dict-values", "constrained-but-undeclared", "marker-on-container-only"],
)
def test_every_shape_of_undeclared_string_is_caught(annotation):
    def tool_fn(ctx, thing):
        pass

    tool_fn.__annotations__ = {"thing": annotation}
    tool_fn.__doc__ = doc("thing")

    with pytest.raises(ToolDefinitionError, match="plain string"):
        extract(tool_fn)


@pytest.mark.parametrize(
    "annotation",
    [ServiceName, TeamName, SearchText, Message, Window, ServiceName | None, list[ServiceName],
     Annotated[str, Verbatim()], Annotated[str, Field(max_length=3), Verbatim()]],
)
def test_declared_strings_are_accepted(annotation):
    def tool_fn(ctx, thing=None):
        pass

    tool_fn.__annotations__ = {"thing": annotation}
    tool_fn.__doc__ = doc("thing")

    assert "thing" in extract(tool_fn)


def test_non_string_parameters_need_no_declaration():
    def tool_fn(ctx, count: int, ratio: float, flag: bool, mode: typing.Literal["a", "b"], many: list[int]):
        pass

    tool_fn.__doc__ = doc("count", "ratio", "flag", "mode", "many")

    assert set(extract(tool_fn)) == {"count", "ratio", "flag", "mode", "many"}


# Written out here, not derived from ENTITY_PARAMETER_NAMES: a test parametrized
# from the constant it guards passes vacuously if that constant is emptied.
RESERVED_NAMES = ["service", "services", "team"]


def test_the_reserved_entity_parameter_names_are_all_present():
    assert set(RESERVED_NAMES) <= ENTITY_PARAMETER_NAMES


@pytest.mark.parametrize("name", RESERVED_NAMES)
def test_a_parameter_named_like_an_entity_cannot_be_declared_verbatim(name):
    namespace: dict = {}
    exec(f"def tool_fn(ctx, {name}): pass", namespace)  # a parameter with exactly this name
    tool_fn = namespace["tool_fn"]
    tool_fn.__annotations__ = {name: Annotated[str, Verbatim()]}
    tool_fn.__doc__ = doc(name)

    with pytest.raises(ToolDefinitionError, match="named like a catalog identifier"):
        extract(tool_fn)


def test_entity_declared_parameters_with_entity_names_are_accepted():
    def get_thing(ctx, service: ServiceName, team: TeamName):
        pass

    get_thing.__doc__ = doc("service", "team")

    assert set(extract(get_thing)) == {"service", "team"}


def test_a_list_of_entities_is_normalized_element_by_element():
    def tool_fn(ctx, services: list[ServiceName]):
        pass

    tool_fn.__doc__ = doc("services")
    param = extract(tool_fn)["services"]

    assert param.adapter.validate_python([" A-B ", "C"]) == ["a-b", "c"]


def test_registering_a_tool_with_an_undeclared_string_fails_at_import_time(isolated_registry):
    def forgetful_tool(ctx, service: str) -> dict:
        pass

    forgetful_tool.__doc__ = doc("service")

    with pytest.raises(ToolDefinitionError, match="plain string"):
        isolated_registry.tool(forgetful_tool)
    assert isolated_registry.registered_tools() == {}


# ----------------------------------------------------------- tool twelve


def test_a_naive_new_tool_is_safe_without_any_normalization_of_its_own(isolated_registry, s_ctx):
    """Tool twelve does the laziest possible thing -- indexes the catalog with
    the raw argument, no require_service, no .strip(), no .lower() -- and is
    still correct, because the argument was normalized before its body ran."""

    def get_tier(ctx, service: ServiceName) -> dict:
        return {"tier": ctx.catalog[service].tier}  # a KeyError for any spelling but the canonical one

    get_tier.__doc__ = doc("service")
    isolated_registry.tool(get_tier)
    toolset = Toolset(s_ctx, isolated_registry.registered_tools())

    for spelling in ("checkout-api", "CHECKOUT-API", "  Checkout-Api\n"):
        assert toolset.call("get_tier", {"service": spelling}) == {"tier": 1}
    assert toolset.functions["get_tier"]("Checkout-API") == {"tier": 1}


def test_the_same_naive_tool_cannot_be_written_with_a_plain_string(isolated_registry):
    def get_tier(ctx, service: str) -> dict:
        return {}

    get_tier.__doc__ = doc("service")

    with pytest.raises(ToolDefinitionError):
        isolated_registry.tool(get_tier)


def test_the_enumeration_sweeps_whatever_the_registry_holds():
    assert set(ENTITY_TOOLS) <= set(TOOL_ORDER)  # a subset, never a count: a new tool must not break this
