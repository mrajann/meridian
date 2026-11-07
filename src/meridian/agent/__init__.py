"""Increment 7: a single agent with all eleven tools, driven by a hand-written loop.

    loop = AgentLoop(client, toolset, catalog)
    run = loop.run(incident_task(alert, scenario.now), incident_id=alert.doc_id)
    run.report   # a validated IncidentReport, or None
    run.trace    # every turn and tool call, as JSON-serialisable pydantic models
"""

from meridian.agent.client import AnthropicClient, ModelClient, ModelResponse, Usage
from meridian.agent.loop import AgentConfig, AgentLoop, AgentRun
from meridian.agent.prompts import SYSTEM_PROMPT, incident_task
from meridian.agent.report import SUBMIT_TOOL_NAME, Citation, IncidentReport, RootCause
from meridian.agent.trace import RunTrace, ToolCallTrace, TurnTrace

__all__ = [
    "SUBMIT_TOOL_NAME",
    "SYSTEM_PROMPT",
    "AgentConfig",
    "AgentLoop",
    "AgentRun",
    "AnthropicClient",
    "Citation",
    "IncidentReport",
    "ModelClient",
    "ModelResponse",
    "RootCause",
    "RunTrace",
    "ToolCallTrace",
    "TurnTrace",
    "Usage",
    "incident_task",
]
