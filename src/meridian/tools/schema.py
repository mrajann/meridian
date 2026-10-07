"""Build Anthropic tool-use schemas, and validate model-supplied arguments,
from a tool function's signature and docstring -- nothing is hand-written.

Conventions a tool function follows (enforced when it is registered):

- first parameter is `ctx` (the ToolContext); it is invisible to the model
- every other parameter is type-annotated; constraints go in the annotation
  (`Annotated[int, Field(ge=1, le=20)]`, `Literal["a", "b"]`)
- every string parameter declares its kind (meridian.tools.types): a catalog
  identifier (ServiceName, TeamName -- normalized before the tool runs) or
  verbatim text. A bare `str` is rejected at registration
- the docstring is Google style: a summary, guidance paragraphs, an `Args:`
  entry for every parameter, and optionally a `Returns:` section

The docstring is the prompt: the model reads the description to choose a
tool and the `Args:` entries to fill it in.
"""

from __future__ import annotations

import collections.abc
import inspect
import re
import types
import typing
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from pydantic import TypeAdapter, ValidationError

from meridian.tools.errors import ToolDefinitionError, ToolError
from meridian.tools.types import ENTITY_PARAMETER_NAMES, CatalogEntity, Verbatim

MIN_DESCRIPTION_CHARS = 200  # a one-liner is not enough for a model to choose well
_SECTION_RE = re.compile(r"^(Args|Returns):\s*$")
_PARAM_RE = re.compile(r"^(\w+):\s*(.*)$")


@dataclass(frozen=True)
class ParsedDocstring:
    description: str  # everything before Args:, plus Returns: appended
    params: dict[str, str]


def parse_docstring(doc: str | None) -> ParsedDocstring:
    lines = inspect.cleandoc(doc or "").splitlines()
    body: list[str] = []
    returns: list[str] = []
    params: dict[str, list[str]] = {}
    section, current = "body", None

    for line in lines:
        match = _SECTION_RE.match(line.strip()) if not line.startswith((" ", "\t")) else None
        if match:
            section, current = match.group(1).lower(), None
            continue
        if section == "body":
            body.append(line)
        elif section == "returns":
            returns.append(line.strip())
        elif section == "args":
            stripped = line.strip()
            if not stripped:
                continue
            param = _PARAM_RE.match(stripped) if not line.startswith("        ") else None
            if param:
                current = param.group(1)
                params[current] = [param.group(2)]
            elif current:
                params[current].append(stripped)

    description = "\n".join(body).strip()
    returns_text = " ".join(part for part in returns if part).strip()
    if returns_text:
        description += f"\n\nReturns: {returns_text}"
    return ParsedDocstring(description, {name: " ".join(p for p in parts if p) for name, parts in params.items()})


def _clean(schema: Any) -> Any:
    """Drop pydantic's `title` noise and collapse `X | None` to X (an optional
    parameter is simply omitted, so the null branch only confuses the model)."""
    if isinstance(schema, list):
        return [_clean(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    schema = {k: _clean(v) for k, v in schema.items() if k != "title"}
    branches = schema.get("anyOf")
    if branches:
        kept = [b for b in branches if b.get("type") != "null"]
        if len(kept) == 1:
            merged = {k: v for k, v in schema.items() if k != "anyOf"}
            merged.update(kept[0])
            return merged
        schema["anyOf"] = kept
    return schema


@dataclass(frozen=True)
class Param:
    name: str
    annotation: Any
    default: Any  # inspect.Parameter.empty if required
    description: str
    adapter: TypeAdapter

    @property
    def required(self) -> bool:
        return self.default is inspect.Parameter.empty

    def schema(self) -> dict[str, Any]:
        prop = _clean(self.adapter.json_schema())
        prop["description"] = self.description
        if not self.required and self.default is not None:
            prop["default"] = self.default
        return prop


_CONTAINERS = (list, set, frozenset, tuple, collections.abc.Sequence, collections.abc.Set)


def _string_leaves(annotation: Any, markers: tuple = ()) -> Iterator[tuple]:
    """Yield, for every `str` the annotation can hold (through Annotated,
    Optional/unions and list/set/tuple/dict), the Annotated metadata attached
    to it. Metadata on a container does not describe its elements."""
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        inner, *metadata = typing.get_args(annotation)
        yield from _string_leaves(inner, markers + tuple(metadata))
    elif origin is typing.Union or origin is types.UnionType:
        for arg in typing.get_args(annotation):
            if arg is not type(None):
                yield from _string_leaves(arg, markers)
    elif origin in _CONTAINERS:
        for arg in typing.get_args(annotation):
            if arg is not Ellipsis:
                yield from _string_leaves(arg)
    elif origin is dict:
        for arg in typing.get_args(annotation)[1:]:
            yield from _string_leaves(arg)
    elif annotation is str:
        yield markers


def check_string_kinds(func_name: str, param: str, annotation: Any) -> None:
    """Every string parameter must declare its kind, and a parameter named
    like a catalog entity must be declared as one. This is what makes the
    normalization in meridian.tools.types impossible to forget: the decision
    cannot be skipped, only made wrongly and visibly."""
    for markers in _string_leaves(annotation):
        is_entity = any(isinstance(m, CatalogEntity) for m in markers)
        if not (is_entity or any(isinstance(m, Verbatim) for m in markers)):
            raise ToolDefinitionError(
                f"{func_name}: parameter `{param}` is a plain string, so its kind is undeclared. Use ServiceName or "
                f"TeamName (catalog identifiers: whitespace stripped and case folded before your code runs) or a "
                f"Verbatim type such as SearchText, Message or Window (free text used as given) from "
                f"meridian.tools.types."
            )
        if param in ENTITY_PARAMETER_NAMES and not is_entity:
            raise ToolDefinitionError(
                f"{func_name}: parameter `{param}` is named like a catalog identifier but declared Verbatim, so it "
                f"would reach the tool in whatever case the model typed. Declare it ServiceName or TeamName."
            )


def extract_params(func: Callable, parsed: ParsedDocstring) -> dict[str, Param]:
    signature = inspect.signature(func)
    names = list(signature.parameters)
    if not names or names[0] != "ctx":
        raise ToolDefinitionError(f"{func.__name__}: first parameter must be `ctx`")
    hints = typing.get_type_hints(func, include_extras=True)

    params: dict[str, Param] = {}
    for name in names[1:]:
        p = signature.parameters[name]
        if name not in hints:
            raise ToolDefinitionError(f"{func.__name__}: parameter `{name}` has no type annotation")
        if name not in parsed.params:
            raise ToolDefinitionError(f"{func.__name__}: parameter `{name}` is missing from the docstring's Args:")
        check_string_kinds(func.__name__, name, hints[name])
        params[name] = Param(name, hints[name], p.default, parsed.params[name], TypeAdapter(hints[name]))

    undocumented_extra = set(parsed.params) - set(params)
    if undocumented_extra:
        raise ToolDefinitionError(f"{func.__name__}: Args: documents unknown parameter(s) {sorted(undocumented_extra)}")
    return params


def build_schema(name: str, description: str, params: dict[str, Param]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": {p.name: p.schema() for p in params.values()},
            "required": [p.name for p in params.values() if p.required],
            "additionalProperties": False,
        },
    }


# ------------------------------------------------------------- validation


def _expected(schema: dict[str, Any]) -> str:
    if "enum" in schema:
        return "one of " + ", ".join(repr(v) for v in schema["enum"])
    kind = schema.get("type", "value")
    if "exclusiveMinimum" in schema or "exclusiveMaximum" in schema:
        return f"{kind} greater than {schema.get('exclusiveMinimum', '-inf')} and less than {schema.get('exclusiveMaximum', 'inf')}"
    if "minimum" in schema or "maximum" in schema:
        return f"{kind} between {schema.get('minimum', '-inf')} and {schema.get('maximum', 'inf')}"
    if "pattern" in schema:
        return f"{kind} matching {schema['pattern']}"
    if "minLength" in schema or "maxLength" in schema:
        low, high = schema.get("minLength", 0), schema.get("maxLength")
        return f"{kind} of {low}-{high} characters" if high is not None else f"{kind} of at least {low} characters"
    return kind


def validate_arguments(tool_name: str, params: dict[str, Param], arguments: dict[str, Any]) -> dict[str, Any]:
    """Coerce and check the model's arguments, reporting *every* problem in one
    message the model can act on instead of failing on the first."""
    problems: list[str] = []
    unknown = sorted(set(arguments) - set(params))
    if unknown:
        problems.append(f"unknown argument(s) {unknown}; this tool accepts {list(params)}")

    kwargs: dict[str, Any] = {}
    for name, param in params.items():
        if name not in arguments:
            if param.required:
                problems.append(f"missing required argument '{name}' ({_expected(param.schema())})")
            continue
        try:
            kwargs[name] = param.adapter.validate_python(arguments[name])
        except ValidationError as exc:
            reason = exc.errors()[0]["msg"]
            hint = param.description if len(param.description) <= 160 else param.description[:157] + "..."
            problems.append(
                f"'{name}'={arguments[name]!r} is invalid: {reason} (expected {_expected(param.schema())}). {hint}"
            )

    if problems:
        raise ToolError(f"{tool_name}: " + "; ".join(problems))
    return kwargs
