"""The agent loop, written out.

    send messages + tool schemas -> read the response -> run every tool_use
    block -> send all the tool_results back in one message -> repeat

until the model submits a valid report or a limit is hit. No framework: each
production failure mode below is a few explicit lines, in the order they
happen.

What the loop guarantees:
- Parallel tool calls: every tool_use block in a response is executed and all
  results go back in a single user message, in block order (the API requires
  one result per tool_use id, together).
- A tool never crashes the run. A rejected call (bad or malformed arguments,
  unknown service) and an exception inside a tool both become `is_error`
  results the model can read and recover from; the trace keeps the full
  traceback for the second kind while the model sees only a generic message.
- A hard cap on model calls. The last allowed call forces `submit_report`
  via tool_choice, so a run that spent its budget gathering still ends with a
  report (typically "insufficient evidence") instead of nothing.
- Output is a validated, grounded `IncidentReport` or an explicit failure
  with a reason; a rejected report is returned to the model to fix.
- Every turn and tool call is traced (trace.py), including on failure.
"""

from __future__ import annotations

import json
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from meridian.agent.client import ModelClient, ModelResponse
from meridian.agent.evidence import EvidenceLedger
from meridian.agent.prompts import SYSTEM_PROMPT, system_prompt_sha
from meridian.agent.output import OutputSpec
from meridian.agent.report import INCIDENT_REPORT_SPEC, SUBMIT_TOOL_NAME, format_validation_error
from meridian.agent.trace import RunTrace, ToolCallTrace, TurnTrace
from meridian.catalog import ServiceEntry
from meridian.tools.registry import Toolset

PLACEHOLDER_TEXT = "(no output)"
NUDGE_TEMPLATE = (
    "You stopped without calling {tool}. Call it now with your findings. If the evidence does not "
    "establish a cause, submit {hint}."
)
DEFAULT_HINT = INCIDENT_REPORT_SPEC.fallback_hint
NUDGE = NUDGE_TEMPLATE.format(tool=SUBMIT_TOOL_NAME, hint=DEFAULT_HINT)
TRUNCATED = (
    "Your last response hit the output limit and any tool calls in it were discarded. Continue, more "
    "concisely, and call the tools again if you still need them."
)
FINAL_TURN_TEMPLATE = (
    "This is your final turn. You must call {tool} now with the best report your evidence supports; "
    "if it does not establish a cause, use {hint}."
)
FINAL_TURN = FINAL_TURN_TEMPLATE.format(tool=SUBMIT_TOOL_NAME, hint=DEFAULT_HINT)


@dataclass(frozen=True)
class AgentConfig:
    max_iterations: int = 12  # model calls, hard cap
    max_tokens: int = 4096  # per model call
    max_nudges: int = 1  # times to prompt a model that stopped without submitting


@dataclass
class AgentRun:
    trace: RunTrace
    report: BaseModel | None = None  # validated output: an IncidentReport unless the loop was given another OutputSpec

    @property
    def ok(self) -> bool:
        return self.report is not None


class AgentLoop:
    def __init__(
        self,
        client: ModelClient,
        toolset: Toolset,
        catalog: dict[str, ServiceEntry],
        *,
        system_prompt: str = SYSTEM_PROMPT,
        config: AgentConfig = AgentConfig(),
        agent_name: str = "single-agent",
        output: OutputSpec = INCIDENT_REPORT_SPEC,
        clock: Callable[[], float] = time.perf_counter,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if config.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        self.client = client
        self.toolset = toolset
        self.catalog = catalog
        self.system_prompt = system_prompt
        self.config = config
        self.agent_name = agent_name
        self._clock = clock
        self._wall_clock = wall_clock
        self.output = output
        self._tools = toolset.schemas() + [output.tool_schema()]

    # ------------------------------------------------------------------ run

    def run(self, task: str, incident_id: str | None = None) -> AgentRun:
        trace = RunTrace(
            run_id=uuid.uuid4().hex[:12],
            agent=self.agent_name,
            incident_id=incident_id,
            model=str(getattr(self.client, "model", "unknown")),
            system_prompt_sha=system_prompt_sha(self.system_prompt),
            tool_names=[t["name"] for t in self._tools],
            task=task,
            started_at=self._wall_clock(),
        )
        run = AgentRun(trace=trace)
        started = self._clock()
        try:
            self._loop(run, task)
        finally:
            trace.duration_ms = _ms(self._clock() - started)
        if run.report is not None:
            trace.status, trace.failure_reason = "completed", None
        return run

    def _loop(self, run: AgentRun, task: str) -> None:
        trace, cfg = run.trace, self.config
        messages: list[dict[str, Any]] = [{"role": "user", "content": task}]
        ledger = EvidenceLedger()
        nudges = 0
        rejected_on_last_turn = False

        for index in range(cfg.max_iterations):
            final_turn = index == cfg.max_iterations - 1
            turn = TurnTrace(
                index=index, agent=self.agent_name, duration_ms=0, input_tokens=0, output_tokens=0, stop_reason=None
            )
            trace.turns.append(turn)
            tool_choice = None
            if final_turn:
                _append_user_text(messages, FINAL_TURN_TEMPLATE.format(tool=self.output.tool_name, hint=self.output.fallback_hint))
                tool_choice = {"type": "tool", "name": self.output.tool_name}
                turn.forced_tool = self.output.tool_name

            called = self._clock()
            try:
                response = self.client.create(
                    system=self.system_prompt,
                    messages=messages,
                    tools=self._tools,
                    max_tokens=cfg.max_tokens,
                    tool_choice=tool_choice,
                )
            except Exception as exc:  # network, auth, rate limit, bad request: the run fails, the process doesn't
                turn.duration_ms = _ms(self._clock() - called)
                turn.error = f"{type(exc).__name__}: {exc}"
                trace.failure_reason = "api_error"
                return
            turn.duration_ms = _ms(self._clock() - called)
            self._record_usage(turn, response)

            blocks = response.content
            turn.text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            tool_uses = [b for b in blocks if b.get("type") == "tool_use"]

            if response.stop_reason == "max_tokens":
                # Any tool_use in a cut-off response may have truncated arguments: run none of it.
                turn.notes.append("truncated_output")
                text_only = [b for b in blocks if b.get("type") == "text"]
                messages.append({"role": "assistant", "content": text_only or [_placeholder()]})
                messages.append({"role": "user", "content": TRUNCATED})
                continue
            if response.stop_reason not in ("tool_use", "end_turn") and not tool_uses:
                turn.notes.append(f"unexpected_stop_reason:{response.stop_reason}")
                trace.failure_reason = "unexpected_stop"
                return

            messages.append({"role": "assistant", "content": blocks or [_placeholder()]})

            if not tool_uses:
                if nudges < cfg.max_nudges:
                    nudges += 1
                    turn.notes.append("nudged_to_submit")
                    messages.append({"role": "user", "content": NUDGE_TEMPLATE.format(tool=self.output.tool_name, hint=self.output.fallback_hint)})
                    continue
                trace.failure_reason = "no_report"
                return

            results, report, rejected_on_last_turn = self._run_tool_uses(tool_uses, turn, ledger)
            if report is not None:
                run.report = report
                return
            messages.append({"role": "user", "content": results})

        trace.failure_reason = "invalid_report" if rejected_on_last_turn else "max_iterations"

    # ---------------------------------------------------------------- tools

    def _run_tool_uses(
        self, tool_uses: list[dict[str, Any]], turn: TurnTrace, ledger: EvidenceLedger
    ) -> tuple[list[dict[str, Any]], BaseModel | None, bool]:
        """Run one response's tool calls. Returns the tool_result blocks (in
        the model's order), the accepted report if one was submitted, and
        whether a submission was rejected."""
        results: list[dict[str, Any] | None] = [None] * len(tool_uses)
        submissions = []
        for position, block in enumerate(tool_uses):
            if block.get("name") == self.output.tool_name:
                submissions.append((position, block))
            else:
                results[position] = self._execute(block, turn, ledger)

        # Submissions are judged last so that evidence gathered in this very
        # response (a search run alongside the submit) counts as seen.
        report: BaseModel | None = None
        rejected = False
        for number, (position, block) in enumerate(submissions):
            result, accepted = self._submit(block, turn, ledger, duplicate=number > 0)
            results[position] = result
            if accepted is not None and report is None:
                report = accepted
            rejected = rejected or (accepted is None and number == 0)
        return [r for r in results if r is not None], report, rejected and report is None

    def _execute(self, block: dict[str, Any], turn: TurnTrace, ledger: EvidenceLedger) -> dict[str, Any]:
        name, arguments, tool_use_id = block.get("name", ""), block.get("input"), block.get("id", "")
        started = self._clock()
        error_kind = detail = None
        if not isinstance(arguments, dict):
            result = _error_result(tool_use_id, f"{name}: arguments must be a JSON object, got {type(arguments).__name__}")
            error_kind = "tool_error"
        else:
            try:
                result = self.toolset.run_tool_use({"id": tool_use_id, "name": name, "input": arguments})
                error_kind = "tool_error" if result["is_error"] else None
            except Exception as exc:  # a bug in a tool: tell the model, keep the traceback for us
                detail = traceback.format_exc()
                error_kind = "internal_error"
                result = _error_result(
                    tool_use_id,
                    f"{name} failed with an internal error ({type(exc).__name__}). This is a fault in the tool, "
                    f"not in your arguments; retrying the same call will not help. Use a different approach.",
                )
        if not result["is_error"]:
            ledger.record(name, arguments, json.loads(result["content"]))
        turn.tool_calls.append(
            ToolCallTrace(
                tool_use_id=tool_use_id,
                name=name,
                arguments=arguments,
                result=result["content"],
                is_error=result["is_error"],
                error_kind=error_kind,
                error_detail=detail,
                duration_ms=_ms(self._clock() - started),
            )
        )
        return result

    def _submit(
        self, block: dict[str, Any], turn: TurnTrace, ledger: EvidenceLedger, *, duplicate: bool
    ) -> tuple[dict[str, Any], BaseModel | None]:
        tool_use_id, arguments = block.get("id", ""), block.get("input")
        started = self._clock()
        report: BaseModel | None = None
        if duplicate:
            result = _error_result(tool_use_id, f"{self.output.tool_name} was already called in this response; call it once.")
        elif not isinstance(arguments, dict):
            result = _error_result(tool_use_id, f"{self.output.tool_name} arguments must be a JSON object")
        else:
            try:
                candidate = self.output.model.model_validate(arguments)
            except ValidationError as exc:
                result = _error_result(tool_use_id, f"report rejected: {format_validation_error(exc)}. Fix and resubmit.")
            else:
                problems = self.output.check(candidate, ledger, self.catalog)
                if problems:
                    result = _error_result(tool_use_id, "report rejected: " + "; ".join(problems) + ". Fix and resubmit.")
                else:
                    report = candidate
                    result = {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps({"status": "accepted"}),
                        "is_error": False,
                    }
        turn.tool_calls.append(
            ToolCallTrace(
                tool_use_id=tool_use_id,
                name=self.output.tool_name,
                arguments=arguments,
                result=result["content"],
                is_error=result["is_error"],
                error_kind="tool_error" if result["is_error"] else None,
                duration_ms=_ms(self._clock() - started),
            )
        )
        return result, report

    @staticmethod
    def _record_usage(turn: TurnTrace, response: ModelResponse) -> None:
        turn.stop_reason = response.stop_reason
        turn.input_tokens = response.usage.input_tokens
        turn.output_tokens = response.usage.output_tokens
        turn.cache_read_tokens = response.usage.cache_read_tokens
        turn.cache_creation_tokens = response.usage.cache_creation_tokens


# --------------------------------------------------------------------- helpers


def _ms(seconds: float) -> float:
    return round(seconds * 1000, 3)


def _placeholder() -> dict[str, Any]:
    return {"type": "text", "text": PLACEHOLDER_TEXT}  # the API rejects an assistant turn with no content


def _error_result(tool_use_id: str, message: str) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": json.dumps({"error": message}),
        "is_error": True,
    }


def _append_user_text(messages: list[dict[str, Any]], text: str) -> None:
    """Add text to the pending user message (tool_results first, then text)."""
    last = messages[-1]
    assert last["role"] == "user"
    if isinstance(last["content"], str):
        last["content"] = f"{last['content']}\n\n{text}"
    else:
        last["content"] = [*last["content"], {"type": "text", "text": text}]
