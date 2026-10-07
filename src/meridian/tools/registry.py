"""Tool registration and dispatch.

`@tool` registers a function (validating its docstring and signature on the
spot). A `Toolset` binds the registered tools to one ToolContext and gives
you what an agent loop needs: the Anthropic `tools=[...]` schemas, and
`run_tool_use()` to turn a model `tool_use` block into a `tool_result` block.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable

from meridian.tools.context import ToolContext
from meridian.tools.errors import ToolDefinitionError, ToolError
from meridian.tools.schema import (
    MIN_DESCRIPTION_CHARS,
    Param,
    build_schema,
    extract_params,
    parse_docstring,
    validate_arguments,
)

_REGISTRY: dict[str, "Tool"] = {}


@dataclass(frozen=True)
class Tool:
    name: str
    func: Callable[..., dict]
    description: str
    params: dict[str, Param]

    def schema(self) -> dict[str, Any]:
        return build_schema(self.name, self.description, self.params)

    def call(self, ctx: ToolContext, arguments: dict[str, Any] | None = None) -> dict:
        return self.func(ctx, **validate_arguments(self.name, self.params, dict(arguments or {})))

    def bind(self, ctx: ToolContext) -> Callable[..., dict]:
        """A plain function with the tool's real signature and docstring (no
        `ctx`), validating its arguments exactly as a model's call would be."""
        names = list(self.params)

        def bound(*args, **kwargs):
            if len(args) > len(names):
                raise TypeError(f"{self.name}() takes at most {len(names)} positional arguments")
            merged = dict(zip(names, args))
            duplicated = set(merged) & set(kwargs)
            if duplicated:
                raise TypeError(f"{self.name}() got multiple values for {sorted(duplicated)}")
            return self.call(ctx, {**merged, **kwargs})

        signature = inspect.signature(self.func)
        bound.__name__, bound.__qualname__, bound.__doc__ = self.name, self.name, self.func.__doc__
        bound.__signature__ = signature.replace(parameters=list(signature.parameters.values())[1:])
        return bound


def tool(func: Callable[..., dict]) -> Callable[..., dict]:
    parsed = parse_docstring(func.__doc__)
    if len(parsed.description) < MIN_DESCRIPTION_CHARS:
        raise ToolDefinitionError(
            f"{func.__name__}: description is {len(parsed.description)} chars; a model choosing between tools "
            f"needs at least {MIN_DESCRIPTION_CHARS} (what it does, when to use it, when not to, what comes back)"
        )
    if func.__name__ in _REGISTRY:
        raise ToolDefinitionError(f"duplicate tool name {func.__name__}")
    _REGISTRY[func.__name__] = Tool(func.__name__, func, parsed.description, extract_params(func, parsed))
    return func


def registered_tools() -> dict[str, Tool]:
    return dict(_REGISTRY)


class Toolset:
    def __init__(self, ctx: ToolContext, tools: dict[str, Tool] | None = None) -> None:
        self.ctx = ctx
        self._tools = tools if tools is not None else registered_tools()
        self.functions: dict[str, Callable[..., dict]] = {name: t.bind(ctx) for name, t in self._tools.items()}

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        """The `tools=[...]` argument for the Anthropic Messages API."""
        return [t.schema() for t in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict:
        if name not in self._tools:
            raise ToolError(f"unknown tool '{name}'; available tools: {self.names}")
        return self._tools[name].call(self.ctx, arguments)

    def run_tool_use(self, tool_use: dict[str, Any]) -> dict[str, Any]:
        """Execute a model `tool_use` content block and return the matching
        `tool_result` block. A ToolError becomes an `is_error` result the
        model can read and retry from; anything else is a bug and propagates."""
        try:
            result, is_error = self.call(tool_use["name"], tool_use.get("input")), False
        except ToolError as exc:
            result, is_error = {"error": str(exc)}, True
        return {
            "type": "tool_result",
            "tool_use_id": tool_use["id"],
            "content": json.dumps(result, default=str),
            "is_error": is_error,
        }

    def __getattr__(self, name: str) -> Callable[..., dict]:
        functions = self.__dict__.get("functions", {})
        if name in functions:
            return functions[name]
        raise AttributeError(name)
