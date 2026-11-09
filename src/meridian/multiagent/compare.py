"""Run either architecture on an incident and get the same fields back.

    summary, trace = run_architecture("single", session, client)
    summary, trace = run_architecture("multi", session, client)

`RunSummary` projects both outputs (an `IncidentReport` from the single agent,
an `IncidentPacket` from the pipeline) onto one shape, plus cost and latency
from their traces, so the two can be set side by side on the same incident.
`score` checks the diagnosis fields against the synthetic world's ground
truth. That is a quick look to compare the architectures with, not the eval
harness: increment 9 builds that (severity accuracy, abstention rate, judge
scoring).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from meridian.agent.client import ModelClient
from meridian.agent.loop import AgentConfig, AgentLoop
from meridian.agent.prompts import incident_task
from meridian.agent.report import IncidentReport
from meridian.agent.session import IncidentSession
from meridian.agent.trace import PipelineTrace, RunTrace
from meridian.multiagent.pipeline import MultiAgentPipeline

Architecture = Literal["single", "multi"]


@dataclass
class RunSummary:
    architecture: Architecture
    incident_id: str
    status: str  # single: completed|failed. multi: completed|partial|failed
    failure: str | None
    severity: str | None
    affected_services: list[str]
    outcome: str | None  # root_cause_identified | insufficient_evidence
    root_cause_service: str | None
    root_cause_category: str | None
    confidence: str | None
    matching_runbook: str | None
    recommended_action: str | None
    escalation_action: str | None  # multi only: the single agent's report carries no paging decision
    pages_made: int  # pages the run actually recorded, from the pager, for both architectures
    customer_headline: str | None  # multi only
    agents: int
    model_calls: int
    tool_calls: int
    tool_errors: int
    input_tokens: int
    output_tokens: int
    duration_ms: float


@dataclass
class Score:
    root_cause_service_correct: bool
    root_cause_category_correct: bool
    runbook_correct: bool  # the right runbook, or no runbook when none exists


def _common(trace: RunTrace | PipelineTrace) -> dict:
    return dict(
        model_calls=trace.model_calls,
        tool_calls=trace.tool_calls,
        tool_errors=trace.tool_errors,
        input_tokens=trace.input_tokens,
        output_tokens=trace.output_tokens,
        duration_ms=trace.duration_ms,
    )


def summarize_single(session: IncidentSession, report: IncidentReport | None, trace: RunTrace) -> RunSummary:
    cause = report.root_cause if report else None
    return RunSummary(
        architecture="single",
        incident_id=session.alert.doc_id,
        status=trace.status,
        failure=trace.failure_reason,
        severity=report.severity if report else None,
        affected_services=list(report.affected_services) if report else [],
        outcome=report.outcome if report else None,
        root_cause_service=cause.service if cause else None,
        root_cause_category=cause.category if cause else None,
        confidence=cause.confidence if cause else None,
        matching_runbook=report.matching_runbook if report else None,
        recommended_action=report.recommended_action if report else None,
        escalation_action=None,
        pages_made=len(session.ctx.pager.records),
        customer_headline=None,
        agents=1,
        **_common(trace),
    )


def summarize_multi(session: IncidentSession, run, trace: PipelineTrace) -> RunSummary:
    packet = run.packet
    cause = packet.investigation.root_cause if packet else None
    return RunSummary(
        architecture="multi",
        incident_id=session.alert.doc_id,
        status=trace.status,
        failure="; ".join(trace.failures) or None,
        severity=packet.triage.severity if packet else None,
        affected_services=list(packet.triage.affected_services) if packet else [],
        outcome=packet.investigation.outcome if packet else None,
        root_cause_service=cause.service if cause else None,
        root_cause_category=cause.category if cause else None,
        confidence=cause.confidence if cause else None,
        matching_runbook=packet.investigation.matching_runbook if packet else None,
        recommended_action=packet.investigation.recommended_action if packet else None,
        escalation_action=packet.escalation.action if packet and packet.escalation else None,
        pages_made=len(session.ctx.pager.records),
        customer_headline=packet.customer_update.headline if packet and packet.customer_update else None,
        agents=len(trace.agents),
        **_common(trace),
    )


def run_architecture(
    architecture: Architecture,
    session: IncidentSession,
    client: ModelClient,
    *,
    max_iterations: int | None = None,
) -> tuple[RunSummary, RunTrace | PipelineTrace]:
    """Run one architecture on one incident. The session's context carries its
    own telemetry and pager, so use a fresh session per run (the pager records
    pages, and a second run in the same session would see the first's)."""
    task_time = session.scenario.now
    if architecture == "single":
        config = AgentConfig(max_iterations=max_iterations) if max_iterations else AgentConfig()
        loop = AgentLoop(client, session.toolset(), session.catalog, config=config)
        run = loop.run(incident_task(session.alert, task_time), incident_id=session.alert.doc_id)
        return summarize_single(session, run.report, run.trace), run.trace
    if architecture == "multi":
        iterations = {name: max_iterations for name in ("triage", "investigator", "escalation", "comms")} if max_iterations else None
        pipeline = MultiAgentPipeline(client, session.ctx, session.catalog, iterations=iterations)
        run = pipeline.run(session.alert, task_time, session.alert.doc_id)
        return summarize_multi(session, run, run.trace), run.trace
    raise ValueError(f"unknown architecture '{architecture}'; use 'single' or 'multi'")


def score(summary: RunSummary, session: IncidentSession) -> Score:
    """Diagnosis fields against ground truth. An abstention (no root cause) is
    scored as not-correct here, since it did not find the cause; increment 9's
    abstention metric treats the no-match incidents separately."""
    truth = session.scenario
    meta = session.alert.metadata
    has_runbook = bool(meta.get("has_matching_runbook"))
    if has_runbook:
        runbook_ok = summary.matching_runbook == meta.get("correct_runbook")
    else:
        runbook_ok = summary.matching_runbook is None
    return Score(
        root_cause_service_correct=summary.root_cause_service == truth.root_cause_service,
        root_cause_category_correct=summary.root_cause_category == truth.category,
        runbook_correct=runbook_ok and summary.status in ("completed", "partial"),
    )


def as_dict(summary: RunSummary, scored: Score) -> dict:
    return {**asdict(summary), **{f"score_{k}": v for k, v in asdict(scored).items()}}
