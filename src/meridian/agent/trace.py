"""Structured trace of an agent run: the observability layer's raw material.

One `RunTrace` per run, one `TurnTrace` per model call, one `ToolCallTrace`
per tool call inside a turn. Everything is plain JSON (`model_dump_json`), so
increment 10 can aggregate latency, tokens and tool error rates without
touching the loop.

`agent` is recorded on the run and on every turn from the start: a single
agent is just a run where it is always the same name, and a multi-agent run
is the same structure with the name changing at agent boundaries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

TRACE_SCHEMA_VERSION = 1

# How a tool call failed. "tool_error": the tool rejected the call (bad
# arguments, unknown service, ...) with a message written for the model.
# "internal_error": the tool raised something it was not meant to; a bug,
# reported to the model as a generic failure and kept in full here.
ErrorKind = Literal["tool_error", "internal_error"]

FailureReason = Literal["api_error", "no_report", "invalid_report", "max_iterations", "unexpected_stop"]


class ToolCallTrace(BaseModel):
    tool_use_id: str
    name: str
    arguments: Any  # exactly what the model sent, even if malformed
    result: str  # exactly what the model was shown (JSON text)
    is_error: bool
    error_kind: ErrorKind | None = None
    error_detail: str | None = None  # traceback for internal errors; never sent to the model
    duration_ms: float


class TurnTrace(BaseModel):
    index: int
    agent: str
    duration_ms: float  # the model call only
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    stop_reason: str | None
    text: str = ""  # the model's prose this turn
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    forced_tool: str | None = None  # set when tool_choice forced a specific tool
    notes: list[str] = Field(default_factory=list)  # loop interventions: nudges, truncation, ...
    error: str | None = None  # set when the model call itself failed


class RunTrace(BaseModel):
    schema_version: int = TRACE_SCHEMA_VERSION
    run_id: str
    agent: str
    incident_id: str | None
    model: str
    system_prompt_sha: str  # short hash: attributes behaviour changes to prompt changes
    tool_names: list[str]
    task: str  # the first user message
    started_at: datetime
    duration_ms: float = 0.0
    status: Literal["completed", "failed"] = "failed"
    failure_reason: FailureReason | None = None
    turns: list[TurnTrace] = Field(default_factory=list)

    @computed_field
    @property
    def input_tokens(self) -> int:
        return sum(t.input_tokens for t in self.turns)

    @computed_field
    @property
    def output_tokens(self) -> int:
        return sum(t.output_tokens for t in self.turns)

    @computed_field
    @property
    def model_calls(self) -> int:
        return len(self.turns)

    @computed_field
    @property
    def tool_calls(self) -> int:
        return sum(len(t.tool_calls) for t in self.turns)

    @computed_field
    @property
    def tool_errors(self) -> int:
        return sum(1 for t in self.turns for c in t.tool_calls if c.is_error)

    def calls(self, name: str | None = None) -> list[ToolCallTrace]:
        return [c for t in self.turns for c in t.tool_calls if name is None or c.name == name]
