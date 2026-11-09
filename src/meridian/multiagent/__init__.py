"""Increment 8: four agents (Triage, Investigator, Escalation, Comms) orchestrated with LangGraph.

    pipeline = MultiAgentPipeline(client, ctx, catalog)
    run = pipeline.run(alert, fired_at)
    run.packet   # an IncidentPacket: triage, investigation, escalation, customer update
    run.trace    # a PipelineTrace: one RunTrace per agent, plus every handoff between them

The single agent from increment 7 (meridian.agent) is unchanged and runs on the same incidents;
`meridian.multiagent.compare` runs either on one incident and returns comparable results.
"""

from meridian.multiagent.pipeline import AGENT_TOOLS, MultiAgentPipeline, PipelineRun, toolset_for
from meridian.multiagent.schemas import (
    CustomerUpdate,
    EscalationDecision,
    IncidentPacket,
    Investigation,
    TriageHandoff,
)

__all__ = [
    "AGENT_TOOLS",
    "CustomerUpdate",
    "EscalationDecision",
    "IncidentPacket",
    "Investigation",
    "MultiAgentPipeline",
    "PipelineRun",
    "TriageHandoff",
    "toolset_for",
]
