"""Build Anthropic tool-use schemas, and validate model-supplied arguments,
from a tool function's signature and docstring -- nothing is hand-written.

Conventions a tool function follows (enforced when it is registered):

- first parameter is `ctx` (the ToolContext); it is invisible to the model
- every other parameter is type-annotated; constraints go in the annotation
  (`Annotated[int, Field(ge=1, le=20)]`, `Literal["a", "b"]`)
- the docstring is Google style: a summary, guidance paragraphs, an `Args:`
  entry for every parameter, and optionally a `Returns:` section

The docstring is the prompt: the model reads the description to choose a
tool and the `Args:` entries to fill it in.
"""

from __future__ import annotations

import inspect
import re
import typing
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import TypeAdapter, ValidationError

from meridian.tools.errors import ToolDefinitionError, ToolError

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
