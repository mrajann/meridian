"""A scripted stand-in for the model: tests and CI run the loop with no network.

Each script entry is one model response. It is either a `ModelResponse`, or a
callable taking the request (so a test can react to what the loop sent, e.g.
cite whichever document a search just returned) and returning one. Every
request is recorded (deep-copied: the loop mutates its message list) so tests
can assert on exactly what the model would have seen.
"""

from __future__ import annotations

import copy
import itertools
from typing import Any, Callable

from meridian.agent.client import ModelResponse, Usage

Script = ModelResponse | Callable[[dict[str, Any]], ModelResponse]

_ids = itertools.count(1)


def tool_use(name: str, arguments: Any, id: str | None = None) -> dict[str, Any]:
    return {"type": "tool_use", "id": id or f"toolu_{next(_ids):04d}", "name": name, "input": arguments}


def text(content: str) -> dict[str, Any]:
    return {"type": "text", "text": content}


def reply(*blocks: dict[str, Any], stop_reason: str | None = None, input_tokens: int = 100, output_tokens: int = 20):
    if stop_reason is None:
        stop_reason = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
    return ModelResponse(list(blocks), stop_reason, Usage(input_tokens, output_tokens))


class ScriptedClient:
    model = "scripted"

    def __init__(self, *script: Script) -> None:
        self._script = list(script)
        self.requests: list[dict[str, Any]] = []

    def create(self, *, system, messages, tools, max_tokens, tool_choice=None) -> ModelResponse:
        request = copy.deepcopy(
            dict(system=system, messages=messages, tools=tools, max_tokens=max_tokens, tool_choice=tool_choice)
        )
        self.requests.append(request)
        if len(self.requests) > len(self._script):
            raise AssertionError(f"scripted client ran out of responses (request #{len(self.requests)})")
        step = self._script[len(self.requests) - 1]
        return step(request) if callable(step) else step
