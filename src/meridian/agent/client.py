"""The model boundary: one small interface the loop talks to.

The loop never imports the Anthropic SDK. It sends plain dicts (messages,
tool schemas) to a `ModelClient` and gets a `ModelResponse` back, so tests
drive it with a scripted client and no network, and a different provider is a
new adapter rather than a loop rewrite. `AnthropicClient` is the one adapter
that touches the SDK, and it flattens SDK objects into the same plain dicts
the loop appends to its message history.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


@dataclass(frozen=True)
class ModelResponse:
    content: list[dict[str, Any]]  # text / tool_use blocks, as plain dicts
    stop_reason: str | None  # "tool_use", "end_turn", "max_tokens", ...
    usage: Usage = Usage()


class ModelClient(Protocol):
    def create(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
        tool_choice: dict[str, Any] | None = None,
    ) -> ModelResponse: ...


class AnthropicClient:
    """Messages API adapter. The model is fixed at construction."""

    def __init__(self, api_key: str, model: str, *, timeout: float = 120.0, max_retries: int = 2) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set; copy .env.example to .env and fill it in")
        import anthropic  # deferred: the loop and its tests need no SDK

        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=max_retries)

    def create(self, *, system, messages, tools, max_tokens, tool_choice=None) -> ModelResponse:
        kwargs: dict[str, Any] = dict(
            model=self.model, system=system, messages=messages, tools=tools, max_tokens=max_tokens
        )
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        response = self._client.messages.create(**kwargs)
        usage = response.usage
        return ModelResponse(
            content=[_block_to_dict(block) for block in response.content],
            stop_reason=response.stop_reason,
            usage=Usage(
                input_tokens=usage.input_tokens or 0,
                output_tokens=usage.output_tokens or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
                cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            ),
        )


def _block_to_dict(block) -> dict[str, Any]:
    # Minimal dicts, not model_dump(): echoing null-valued SDK fields back
    # into the next request is needless risk.
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    return block.model_dump(exclude_none=True)
