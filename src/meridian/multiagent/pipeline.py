"""The four-agent pipeline, orchestrated with LangGraph.

    START -> triage -> investigator -> escalation -> comms -> END
                 \\-> END  (if Triage fails: there is nothing to hand on)

Each node is one agent: the same hand-written loop from increment 7
(`meridian.agent.loop.AgentLoop`), run with that agent's own toolset, system
prompt and output schema. LangGraph owns only the wiring: which node runs
next, and the shared state the handoffs travel in. It does not call the model.

Handoffs are the validated outputs of the previous agents, serialised once
(`_hand_off`) and recorded in the trace as exactly the JSON the next agent is
shown. Failure policy:

- Triage fails      -> the run ends (status "failed"); there is no blast radius to hand on.
- Investigator fails -> a system-written Investigation (outcome=insufficient_evidence, flagged
  `system_fallback`) goes on, so Escalation can still page on severity alone.
  A failed investigation must never silently suppress paging for a SEV1.
- Escalation or Comms fails -> the packet is returned without that part (status "partial"). Comms
  still runs when Escalation failed, and is told no decision is available.
"""

from __future__ import annotations

import operator
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError

from meridian.agent.client import ModelClient
from meridian.agent.loop import AgentConfig, AgentLoop, AgentRun
from meridian.agent.output import OutputSpec
from meridian.agent.trace import HandoffSource, HandoffTrace, PipelineTrace, RunTrace
from meridian.catalog import ServiceEntry
from meridian.corpus.models import CorpusDocument
from meridian.multiagent import prompts
from meridian.multiagent.schemas import (
    ESCALATION_SPEC,
    INVESTIGATION_SPEC,
    TRIAGE_SPEC,
    CustomerUpdate,
    EscalationDecision,
    IncidentPacket,
    Investigation,
    TriageHandoff,
    comms_spec,
)
from meridian.tools.context import ToolContext
from meridian.tools.registry import Toolset, registered_tools

TRIAGE, INVESTIGATOR, ESCALATION, COMMS = "triage", "investigator", "escalation", "comms"

# Each agent's tools. These lists are the architecture: an agent cannot call a
# tool that is not here (the toolset rejects it as unknown).
AGENT_TOOLS: dict[str, tuple[str, ...]] = {
    TRIAGE: ("get_service", "get_dependencies", "get_dependents", "query_metrics"),
    INVESTIGATOR: (
        "search_runbooks",
        "search_postmortems",
        "find_similar_incidents",
        "get_deploy_history",
        "query_metrics",
    ),
    ESCALATION: ("get_oncall", "compute_error_budget", "get_service", "page_oncall"),
    COMMS: (),  # deliberately none: Comms sees only what the others found
}

DEFAULT_ITERATIONS = {TRIAGE: 8, INVESTIGATOR: 12, ESCALATION: 8, COMMS: 3}


class PipelineState(TypedDict, total=False):
    triage: TriageHandoff
    investigation: Investigation
    investigation_source: str
    escalation: EscalationDecision
    update: CustomerUpdate
    # Appended to by every node (operator.add merges the partial updates).
    agents: Annotated[list[RunTrace], operator.add]
    handoffs: Annotated[list[HandoffTrace], operator.add]
    path: Annotated[list[str], operator.add]
    failures: Annotated[list[str], operator.add]


@dataclass
class PipelineRun:
    trace: PipelineTrace
    packet: IncidentPacket | None = None

    @property
    def ok(self) -> bool:
        return self.packet is not None


def toolset_for(agent: str, ctx: ToolContext) -> Toolset:
    registry = registered_tools()
    return Toolset(ctx, {name: registry[name] for name in AGENT_TOOLS[agent]})


class MultiAgentPipeline:
    def __init__(
        self,
        client: ModelClient,
        ctx: ToolContext,
        catalog: dict[str, ServiceEntry],
        *,
        iterations: dict[str, int] | None = None,
        max_tokens: int = AgentConfig.max_tokens,
        clock: Callable[[], float] = time.perf_counter,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.client, self.ctx, self.catalog = client, ctx, catalog
        self._iterations = {**DEFAULT_ITERATIONS, **(iterations or {})}
        self._max_tokens = max_tokens
        self._clock = clock
        self._wall_clock = wall_clock
        self._alert: CorpusDocument | None = None
        self._fired_at: datetime | None = None
        self.graph = self._build_graph()

    # ------------------------------------------------------------- the graph

    def _build_graph(self):
        graph = StateGraph(PipelineState)
        graph.add_node(TRIAGE, self._triage)
        graph.add_node(INVESTIGATOR, self._investigator)
        graph.add_node(ESCALATION, self._escalation)
        graph.add_node(COMMS, self._comms)
        graph.add_edge(START, TRIAGE)
        graph.add_conditional_edges(
            TRIAGE, lambda state: INVESTIGATOR if "triage" in state else END, [INVESTIGATOR, END]
        )
        graph.add_edge(INVESTIGATOR, ESCALATION)
        graph.add_edge(ESCALATION, COMMS)
        graph.add_edge(COMMS, END)
        return graph.compile()

    def run(self, alert: CorpusDocument, fired_at: datetime, incident_id: str | None = None) -> PipelineRun:
        self._alert, self._fired_at = alert, fired_at
        trace = PipelineTrace(
            run_id=uuid.uuid4().hex[:12],
            incident_id=incident_id or alert.doc_id,
            model=str(getattr(self.client, "model", "unknown")),
            started_at=self._wall_clock(),
        )
        started = self._clock()
        try:
            state = self.graph.invoke({"agents": [], "handoffs": [], "path": [], "failures": []})
        finally:
            trace.duration_ms = round((self._clock() - started) * 1000, 3)
        trace.agents, trace.handoffs = state["agents"], state["handoffs"]
        trace.path, trace.failures = state["path"], state["failures"]

        if "triage" not in state:
            return PipelineRun(trace)
        packet = IncidentPacket(
            incident_id=trace.incident_id,
            status="completed" if not trace.failures else "partial",
            triage=state["triage"],
            investigation=state["investigation"],
            investigation_source=state.get("investigation_source", "agent"),
            escalation=state.get("escalation"),
            customer_update=state.get("update"),
        )
        trace.status = packet.status
        return PipelineRun(trace, packet)

    # ----------------------------------------------------------------- nodes

    def _triage(self, state: PipelineState) -> dict[str, Any]:
        task = prompts.triage_task(self._alert, self._fired_at)
        run = self._run_agent(TRIAGE, prompts.TRIAGE_PROMPT, TRIAGE_SPEC, task)
        update: dict[str, Any] = {"agents": [run.trace], "path": [TRIAGE]}
        if run.report is None:
            return {**update, "failures": [f"{TRIAGE}: {run.trace.failure_reason}"]}
        handoffs = [self._hand_off(TRIAGE, to, TriageHandoff, run.report) for to in (INVESTIGATOR, ESCALATION, COMMS)]
        if any(h.payload is None for h in handoffs):
            return {**update, "handoffs": handoffs, "failures": [f"{TRIAGE}: invalid handoff"]}
        return {**update, "triage": run.report, "handoffs": handoffs}

    def _investigator(self, state: PipelineState) -> dict[str, Any]:
        triage_payload = _payload(state["handoffs"], TRIAGE, INVESTIGATOR)
        task = prompts.investigator_task(self._alert, self._fired_at, triage_payload)
        run = self._run_agent(INVESTIGATOR, prompts.INVESTIGATOR_PROMPT, INVESTIGATION_SPEC, task)
        update: dict[str, Any] = {"agents": [run.trace], "path": [INVESTIGATOR]}

        investigation, source = run.report, "agent"
        failures: list[str] = []
        if investigation is None:
            failures.append(f"{INVESTIGATOR}: {run.trace.failure_reason}")
            investigation, source = _fallback_investigation(run.trace.failure_reason), "system_fallback"
        handoffs = [self._hand_off(INVESTIGATOR, to, Investigation, investigation, source) for to in (ESCALATION, COMMS)]
        return {
            **update,
            "investigation": investigation,
            "investigation_source": source,
            "handoffs": handoffs,
            "failures": failures,
        }

    def _escalation(self, state: PipelineState) -> dict[str, Any]:
        task = prompts.escalation_task(
            self._alert,
            self._fired_at,
            _payload(state["handoffs"], TRIAGE, ESCALATION),
            _payload(state["handoffs"], INVESTIGATOR, ESCALATION),
        )
        run = self._run_agent(ESCALATION, prompts.ESCALATION_PROMPT, ESCALATION_SPEC, task)
        update: dict[str, Any] = {"agents": [run.trace], "path": [ESCALATION]}
        if run.report is None:
            return {**update, "failures": [f"{ESCALATION}: {run.trace.failure_reason}"]}
        return {**update, "escalation": run.report, "handoffs": [self._hand_off(ESCALATION, COMMS, EscalationDecision, run.report)]}

    def _comms(self, state: PipelineState) -> dict[str, Any]:
        update: dict[str, Any] = {"path": [COMMS]}
        # A failed Escalation must not stop customers hearing about an incident:
        # Comms runs without its decision and is told so.
        task = prompts.comms_task(
            _payload(state["handoffs"], TRIAGE, COMMS),
            _payload(state["handoffs"], INVESTIGATOR, COMMS),
            _payload_or_none(state["handoffs"], ESCALATION, COMMS),
        )
        run = self._run_agent(COMMS, prompts.COMMS_PROMPT, comms_spec(state["investigation"]), task)
        update["agents"] = [run.trace]
        if run.report is None:
            return {**update, "failures": [f"{COMMS}: {run.trace.failure_reason}"]}
        output = self._hand_off(COMMS, "output", CustomerUpdate, run.report)
        return {**update, "update": run.report, "handoffs": [output]}

    # --------------------------------------------------------------- helpers

    def _run_agent(self, agent: str, system_prompt: str, output: OutputSpec, task: str) -> AgentRun:
        loop = AgentLoop(
            self.client,
            toolset_for(agent, self.ctx),
            self.catalog,
            system_prompt=system_prompt,
            config=AgentConfig(max_iterations=self._iterations[agent], max_tokens=self._max_tokens),
            agent_name=agent,
            output=output,
            clock=self._clock,
            wall_clock=self._wall_clock,
        )
        return loop.run(task, incident_id=self._alert.doc_id)

    @staticmethod
    def _hand_off(
        from_agent: str,
        to_agent: str,
        schema: type[BaseModel],
        value: BaseModel,
        source: HandoffSource = "agent",
    ) -> HandoffTrace:
        """Validate a handoff against its schema at the boundary and record
        exactly what is passed on. The payload here is the JSON the receiving
        agent is shown."""
        try:
            payload = schema.model_validate(value.model_dump()).model_dump(mode="json")
            return HandoffTrace(
                from_agent=from_agent, to_agent=to_agent, schema_name=schema.__name__, source=source,
                valid=True, payload=payload,
            )
        except ValidationError as exc:  # unreachable unless a schema and its validator disagree: a bug, recorded
            return HandoffTrace(
                from_agent=from_agent, to_agent=to_agent, schema_name=schema.__name__, source=source,
                valid=False, payload=None, error=str(exc),
            )


def _payload_or_none(handoffs: list[HandoffTrace], from_agent: str, to_agent: str) -> dict[str, Any] | None:
    for handoff in handoffs:
        if (handoff.from_agent, handoff.to_agent) == (from_agent, to_agent):
            return handoff.payload
    return None


def _payload(handoffs: list[HandoffTrace], from_agent: str, to_agent: str) -> dict[str, Any]:
    payload = _payload_or_none(handoffs, from_agent, to_agent)
    if payload is None:
        raise LookupError(f"no handoff from {from_agent} to {to_agent}")
    return payload


def _fallback_investigation(reason: str | None) -> Investigation:
    """What the pipeline passes on when the Investigator produced nothing:
    an honest "unknown", never a guess, so Escalation can still decide on
    severity alone."""
    return Investigation(
        outcome="insufficient_evidence",
        evidence_gaps=[f"The automated investigation did not complete ({reason}); no root-cause analysis exists."],
        recommended_action="Investigate manually: the automated investigation failed before reaching a conclusion.",
    )
