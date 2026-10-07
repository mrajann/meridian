"""Schema generation and argument validation, plus structural checks on the
real registry: every tool's schema is derived from its signature and the
docstring that the model reads."""

import inspect
import json
import re
from typing import Annotated, Literal

import pytest
from pydantic import Field

from meridian.telemetry import METRICS
from meridian.tools import TOOL_ORDER, ToolDefinitionError, ToolError, registered_tools
from meridian.tools import registry as registry_module
from meridian.tools.schema import build_schema, extract_params, parse_docstring, validate_arguments

SPEC_SIGNATURES = {  # meridian-spec.md section 6
    "search_runbooks": ["query", "k"],
    "search_postmortems": ["query", "k"],
    "find_similar_incidents": ["description", "k"],
    "get_service": ["name"],
    "get_dependencies": ["name", "depth"],
    "get_dependents": ["name", "depth"],
    "query_metrics": ["service", "metric", "window"],
    "get_deploy_history": ["service", "window"],
    "compute_error_budget": ["service", "slo_target", "window_days"],
    "get_oncall": ["team"],
    "page_oncall": ["team", "severity", "message"],
}

LONG_DESCRIPTION = "x" * 250


def demo(ctx, query: Annotated[str, Field(min_length=1)], k: Annotated[int, Field(ge=1, le=20)] = 5,
         kind: Literal["a", "b"] | None = None):
    """Search things.

    Use this when X. Do not use it for Y.

    Args:
        query: what to search for.
        k: how many results.
            Continues on a second line.
        kind: optional filter.

    Returns:
        A dict of results.
    """


@pytest.fixture
def demo_params():
    parsed = parse_docstring(demo.__doc__)
    return parsed, extract_params(demo, parsed)


# ------------------------------------------------------------ docstring parsing


def test_parse_docstring_separates_description_and_per_parameter_docs(demo_params):
    parsed, _ = demo_params

    assert parsed.description.startswith("Search things.")
    assert "Do not use it for Y." in parsed.description
    assert parsed.params == {
        "query": "what to search for.",
        "k": "how many results. Continues on a second line.",
        "kind": "optional filter.",
    }


def test_parse_docstring_appends_returns_to_the_description(demo_params):
    assert demo_params[0].description.endswith("Returns: A dict of results.")


def test_parse_docstring_tolerates_a_missing_docstring():
    parsed = parse_docstring(None)

    assert parsed.description == "" and parsed.params == {}


# --------------------------------------------------------------- schema output


def test_schema_has_the_anthropic_shape(demo_params):
    parsed, params = demo_params

    schema = build_schema("demo", parsed.description, params)

    assert set(schema) == {"name", "description", "input_schema"}
    assert schema["input_schema"]["type"] == "object"
    assert schema["input_schema"]["additionalProperties"] is False


def test_required_comes_from_the_absence_of_a_default(demo_params):
    parsed, params = demo_params

    assert build_schema("demo", "d", params)["input_schema"]["required"] == ["query"]


def test_annotation_constraints_flow_into_the_schema(demo_params):
    _, params = demo_params
    props = build_schema("demo", "d", params)["input_schema"]["properties"]

    assert props["k"]["minimum"] == 1 and props["k"]["maximum"] == 20 and props["k"]["type"] == "integer"
    assert props["query"]["minLength"] == 1
    assert props["kind"]["enum"] == ["a", "b"]


def test_optional_parameters_drop_the_null_branch_and_every_property_has_a_description(demo_params):
    _, params = demo_params
    props = build_schema("demo", "d", params)["input_schema"]["properties"]

    assert "anyOf" not in props["kind"]
    assert all(p["description"] for p in props.values())


def test_defaults_are_published_but_a_none_default_is_not(demo_params):
    _, params = demo_params
    props = build_schema("demo", "d", params)["input_schema"]["properties"]

    assert props["k"]["default"] == 5
    assert "default" not in props["kind"]


def test_ctx_never_appears_in_a_schema(demo_params):
    _, params = demo_params

    assert "ctx" not in build_schema("demo", "d", params)["input_schema"]["properties"]


# ------------------------------------------------------------ definition checks


def test_first_parameter_must_be_ctx():
    def bad(query: str):
        """x"""

    with pytest.raises(ToolDefinitionError, match="first parameter must be `ctx`"):
        extract_params(bad, parse_docstring(bad.__doc__))


def test_every_parameter_must_be_annotated():
    def bad(ctx, query):
        """x

        Args:
            query: q.
        """

    with pytest.raises(ToolDefinitionError, match="no type annotation"):
        extract_params(bad, parse_docstring(bad.__doc__))


def test_every_parameter_must_be_documented():
    def bad(ctx, query: str, k: int = 1):
        """x

        Args:
            query: q.
        """

    with pytest.raises(ToolDefinitionError, match="`k` is missing from the docstring"):
        extract_params(bad, parse_docstring(bad.__doc__))


def test_documenting_a_parameter_that_does_not_exist_is_rejected():
    def bad(ctx, query: str):
        """x

        Args:
            query: q.
            ghost: not a parameter.
        """

    with pytest.raises(ToolDefinitionError, match="unknown parameter"):
        extract_params(bad, parse_docstring(bad.__doc__))


def test_registering_a_thin_description_is_rejected(monkeypatch):
    monkeypatch.setattr(registry_module, "_REGISTRY", {})

    def thin(ctx, query: str):
        """Searches stuff.

        Args:
            query: q.
        """

    with pytest.raises(ToolDefinitionError, match="at least 200"):
        registry_module.tool(thin)


def test_registering_a_duplicate_name_is_rejected(monkeypatch):
    monkeypatch.setattr(registry_module, "_REGISTRY", {})

    def dupe(ctx, query: str):
        f'''{LONG_DESCRIPTION}

        Args:
            query: q.
        '''

    dupe.__doc__ = f"{LONG_DESCRIPTION}\n\nArgs:\n    query: q.\n"
    registry_module.tool(dupe)

    with pytest.raises(ToolDefinitionError, match="duplicate"):
        registry_module.tool(dupe)


# ------------------------------------------------------------------ validation


def test_validation_coerces_compatible_values(demo_params):
    _, params = demo_params

    assert validate_arguments("demo", params, {"query": "x", "k": "7"}) == {"query": "x", "k": 7}


def test_validation_omits_arguments_that_were_not_supplied(demo_params):
    _, params = demo_params

    assert validate_arguments("demo", params, {"query": "x"}) == {"query": "x"}


def test_validation_reports_every_problem_at_once(demo_params):
    _, params = demo_params

    with pytest.raises(ToolError) as exc:
        validate_arguments("demo", params, {"k": 99, "kind": "z", "bogus": 1})

    message = str(exc.value)
    assert "unknown argument(s) ['bogus']" in message
    assert "missing required argument 'query'" in message
    assert "'k'=99" in message and "between 1 and 20" in message
    assert "'kind'='z'" in message and "one of 'a', 'b'" in message


def test_validation_errors_carry_the_parameters_own_description_as_a_hint(demo_params):
    _, params = demo_params

    with pytest.raises(ToolError, match="how many results"):
        validate_arguments("demo", params, {"query": "x", "k": 0})


# ------------------------------------------------------------- the real registry


def test_all_eleven_tools_are_registered_in_the_specs_order():
    assert list(registered_tools()) == TOOL_ORDER
    assert len(TOOL_ORDER) == 11


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_signatures_match_the_spec(name):
    assert list(registered_tools()[name].params) == SPEC_SIGNATURES[name]


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_schema_is_derived_from_the_real_signature(name):
    tool = registered_tools()[name]
    signature = inspect.signature(tool.func)
    expected_required = [
        p for p, param in list(signature.parameters.items())[1:] if param.default is inspect.Parameter.empty
    ]

    schema = tool.schema()["input_schema"]

    assert schema["required"] == expected_required
    assert list(schema["properties"]) == list(signature.parameters)[1:]


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_schema_satisfies_the_anthropic_tool_contract(name):
    schema = registered_tools()[name].schema()

    assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", schema["name"])
    assert schema["input_schema"]["type"] == "object"
    assert set(schema["input_schema"]["required"]) <= set(schema["input_schema"]["properties"])
    assert schema["input_schema"]["additionalProperties"] is False
    assert all(p.get("description") for p in schema["input_schema"]["properties"].values())
    json.dumps(schema)  # must be serializable to send


@pytest.mark.parametrize("name", TOOL_ORDER)
def test_descriptions_are_substantial_and_say_when_not_to_use_the_tool(name):
    description = registered_tools()[name].description

    assert len(description) >= 200
    assert "Do not use" in description, "a model choosing between tools needs to be told what each one is NOT for"


def test_query_metrics_documents_and_enumerates_exactly_the_real_metrics():
    tool = registered_tools()["query_metrics"]

    enum = tool.schema()["input_schema"]["properties"]["metric"]["enum"]

    assert set(enum) == set(METRICS)
    for metric in METRICS:  # the docstring is the prompt: drift here silently hides a metric from the model
        assert metric in tool.description


def test_severity_enum_and_message_bounds_are_in_the_page_schema():
    props = registered_tools()["page_oncall"].schema()["input_schema"]["properties"]

    assert props["severity"]["enum"] == ["SEV1", "SEV2", "SEV3", "SEV4"]
    assert props["message"]["minLength"] == 20 and props["message"]["maxLength"] == 500


def test_slo_target_schema_is_a_percentage_not_a_fraction():
    props = registered_tools()["compute_error_budget"].schema()["input_schema"]["properties"]

    assert props["slo_target"]["exclusiveMinimum"] == 1 and props["slo_target"]["exclusiveMaximum"] == 100
    assert "slo_target" not in registered_tools()["compute_error_budget"].schema()["input_schema"]["required"]
    assert props["window_days"]["minimum"] == 7 and props["window_days"]["default"] == 30
