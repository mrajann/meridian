"""The agent's structured output, and the checks that make it trustworthy.

Two layers, both reported back to the model so it can fix and resubmit:

1. Shape (`IncidentReport`, pydantic): severity is SEV1-4, services are
   normalized identifiers, a diagnosis must carry a hypothesis with
   citations, and an "insufficient evidence" report must say what is missing
   and must NOT carry a hypothesis -- the two outcomes cannot be blurred.
2. Grounding (`check_report`): every service must exist in the catalog and
   every citation must point at evidence this investigation actually
   retrieved (see evidence.py). A plausible-sounding citation to a document
   the agent never saw is rejected, not trusted.
"""

from __future__ import annotations

import difflib
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from meridian.agent.evidence import EvidenceLedger
from meridian.agent.output import OutputSpec, inline_schema
from meridian.catalog import ServiceEntry
from meridian.corpus.taxonomy import CATEGORY_INFO
from meridian.tools.types import ServiceName

Severity = Literal["SEV1", "SEV2", "SEV3", "SEV4"]
Outcome = Literal["root_cause_identified", "insufficient_evidence"]
Confidence = Literal["high", "medium", "low"]
# The failure modes the platform knows about, plus an explicit escape hatch so
# the model is never forced to mislabel something genuinely new.
Category = Literal[tuple(CATEGORY_INFO) + ("other",)]  # type: ignore[valid-type]

SUBMIT_TOOL_NAME = "submit_report"


class Citation(BaseModel):
    kind: Literal["document", "deploy", "metric", "catalog"] = Field(
        description=(
            "What is cited. document: a doc_id returned by a search tool. deploy: a deploy_id from "
            "get_deploy_history. metric: 'service/metric_name' for a series you queried with query_metrics. "
            "catalog: a service name you looked up with get_service, get_dependencies or get_dependents."
        )
    )
    ref: str = Field(
        min_length=1,
        description="The identifier: doc_id, deploy_id, 'service/metric', or service name. Copy it exactly.",
    )
    supports: str = Field(
        min_length=10, max_length=300, description="The specific claim in your report this evidence supports."
    )


class RootCause(BaseModel):
    service: ServiceName = Field(
        description="The service where the fault originates. Under a cascade this is the upstream root, not "
        "the services that merely show symptoms."
    )
    category: Category = Field(description="The failure mode. Use 'other' only if none of the listed fits.")
    summary: str = Field(
        min_length=20, max_length=600, description="What is going wrong and why, in plain technical terms."
    )
    confidence: Confidence = Field(
        description="high: telemetry and at least one retrieved document agree. medium: one line of evidence "
        "or a plausible-but-unconfirmed match. low: a guess you could not corroborate."
    )
    citations: list[Citation] = Field(
        min_length=1,
        max_length=10,
        description="Evidence for this hypothesis. Every cited item must have been returned by a tool during "
        "this investigation.",
    )


class IncidentReport(BaseModel):
    severity: Severity = Field(
        description="SEV1: a tier-1 service is down or severely degraded for customers (checkout, auth, payments). "
        "SEV2: a tier-1 service is partly degraded, or a tier-2 service is down. SEV3: limited or internal "
        "impact, or degradation with a working fallback. SEV4: no customer impact."
    )
    severity_rationale: str = Field(
        min_length=10, max_length=400, description="Why this severity, in one or two sentences."
    )
    affected_services: list[ServiceName] = Field(
        min_length=1,
        description="Every service with customer- or system-visible impact, including the root cause service "
        "itself and everything downstream that is actually degraded.",
    )
    outcome: Outcome = Field(
        description="root_cause_identified: you have a hypothesis supported by cited evidence. "
        "insufficient_evidence: you could not establish a cause; say so rather than guess."
    )
    root_cause: RootCause | None = Field(
        default=None, description="Required when outcome is root_cause_identified; must be null otherwise."
    )
    evidence_gaps: list[Annotated[str, Field(min_length=10, max_length=300)]] = Field(
        default_factory=list,
        max_length=6,
        description="What is missing or contradictory. Required (at least one) when outcome is "
        "insufficient_evidence; optional caveats otherwise.",
    )
    matching_runbook: str | None = Field(
        default=None,
        description="doc_id of a retrieved runbook that actually addresses this incident, or null if none does. "
        "Null is a legitimate, valuable answer: a runbook about a different failure is not a match. This is "
        "independent of outcome: you can know the cause and still have no runbook for it.",
    )
    recommended_action: str = Field(
        min_length=20,
        max_length=800,
        description="What the on-call should do next. With insufficient_evidence, say what to investigate "
        "or who to bring in.",
    )

    @model_validator(mode="after")
    def _outcome_matches_contents(self) -> IncidentReport:
        check_outcome_consistency(self.outcome, self.root_cause, self.evidence_gaps)
        return self


def check_outcome_consistency(outcome: str, root_cause: RootCause | None, evidence_gaps: list[str]) -> None:
    """The rule that keeps "diagnosed" and "unknown" distinct, shared by every
    output that carries an outcome."""
    if outcome == "root_cause_identified" and root_cause is None:
        raise ValueError("outcome is root_cause_identified but root_cause is missing")
    if outcome == "insufficient_evidence":
        if root_cause is not None:
            raise ValueError(
                "outcome is insufficient_evidence but root_cause is set; either you have a supported "
                "hypothesis (outcome=root_cause_identified) or you do not (root_cause=null)"
            )
        if not evidence_gaps:
            raise ValueError("outcome is insufficient_evidence but evidence_gaps is empty; say what is missing")


def report_input_schema() -> dict[str, Any]:
    """JSON Schema for the submit tool's input (see output.inline_schema)."""
    return inline_schema(IncidentReport)


SUBMIT_DESCRIPTION = (
    "Submit your final incident report. Call this exactly once, when you have enough to answer or have "
    "established that you cannot. Ends the investigation. Every citation must refer to evidence returned "
    "by your other tool calls; a report citing anything else is rejected and you must fix it. Use "
    "outcome=insufficient_evidence, not a guess, when the evidence does not support a cause. Do not "
    "call this to ask a question or to report progress."
)


def submit_tool_schema() -> dict[str, Any]:
    return {"name": SUBMIT_TOOL_NAME, "description": SUBMIT_DESCRIPTION, "input_schema": report_input_schema()}


def format_validation_error(error: ValidationError, limit: int = 8) -> str:
    problems = []
    for item in error.errors()[:limit]:
        where = ".".join(str(p) for p in item["loc"]) or "report"
        problems.append(f"{where}: {item['msg']}")
    more = len(error.errors()) - limit
    return "; ".join(problems) + (f"; ...and {more} more" if more > 0 else "")


def unknown_services(names: list[str], where: str, catalog: dict[str, ServiceEntry]) -> list[str]:
    problems = []
    for name in names:
        if name not in catalog:
            near = difflib.get_close_matches(name, catalog, n=3)
            hint = f" Did you mean {near}?" if near else ""
            problems.append(f"{where}: '{name}' is not a service in the catalog.{hint}")
    return problems


def ungrounded_citations(citations: list[Citation], ledger: EvidenceLedger) -> list[str]:
    return [
        f"citation {c.kind} '{c.ref}' was not returned by any tool call in this investigation. "
        f"Cite only evidence you retrieved, copied exactly."
        for c in citations
        if not ledger.has(c.kind, c.ref)
    ]


def check_runbook(matching_runbook: str | None, ledger: EvidenceLedger) -> list[str]:
    if matching_runbook is None:
        return []
    doc_type = ledger.documents.get(matching_runbook)
    if doc_type is None:
        return [f"matching_runbook '{matching_runbook}' was not returned by any search"]
    if doc_type != "runbook":
        return [f"matching_runbook '{matching_runbook}' is a {doc_type}, not a runbook"]
    return []


def check_report(report: IncidentReport, ledger: EvidenceLedger, catalog: dict[str, ServiceEntry]) -> list[str]:
    """Grounding problems with a structurally valid report (empty = grounded)."""
    problems = unknown_services(report.affected_services, "affected_services", catalog)
    if report.root_cause:
        problems += unknown_services([report.root_cause.service], "root_cause.service", catalog)
        problems += ungrounded_citations(report.root_cause.citations, ledger)
    return problems + check_runbook(report.matching_runbook, ledger)


INCIDENT_REPORT_SPEC = OutputSpec(
    tool_name=SUBMIT_TOOL_NAME,
    description=SUBMIT_DESCRIPTION,
    model=IncidentReport,
    check=check_report,
)
