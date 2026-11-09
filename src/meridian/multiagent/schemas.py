"""The structured handoffs between the four agents, and the checks on each.

Every agent submits one of these through its own submit tool; the loop
validates the shape (pydantic) and then runs the agent's grounding check
against what it actually retrieved, returning problems to the model to fix. A
handoff that reaches the next agent has therefore passed both. Nothing between
agents is free text except fields inside these schemas.

    Triage --TriageHandoff--+--> Investigator --Investigation--+--> Escalation --EscalationDecision--+
                            +----------------------------------+----------------------------------->+--> Comms --CustomerUpdate
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from meridian.agent.evidence import EvidenceLedger
from meridian.agent.output import OutputSpec
from meridian.agent.report import (
    Citation,
    Outcome,
    RootCause,
    Severity,
    check_outcome_consistency,
    check_runbook,
    ungrounded_citations,
    unknown_services,
)
from meridian.catalog import ServiceEntry
from meridian.tools.types import ServiceName, TeamName

Gap = Annotated[str, Field(min_length=10, max_length=300)]

# ------------------------------------------------------------------- Triage


class TriageHandoff(BaseModel):
    severity: Severity = Field(
        description="SEV1: a tier-1 service is down or severely degraded for customers (checkout, auth, payments). "
        "SEV2: a tier-1 service is partly degraded, or a tier-2 service is down. SEV3: limited or internal "
        "impact, or degradation with a working fallback. SEV4: no customer impact."
    )
    severity_rationale: str = Field(
        min_length=10, max_length=400, description="Why this severity: which tier is affected and how badly."
    )
    cascade: bool = Field(
        description="True when several services are failing because of one shared upstream problem, rather "
        "than each failing on its own."
    )
    affected_services: list[ServiceName] = Field(
        min_length=1,
        description="Services that are degraded right now, confirmed by telemetry or the alert itself.",
    )
    investigation_targets: list[ServiceName] = Field(
        min_length=1,
        max_length=5,
        description="Where the Investigator should look for the root cause, most likely first. For a cascade "
        "this is the shared upstream service, NOT the services showing symptoms. For a failure confined to one "
        "service it is that service, or the dependency it points at when its own metrics look healthy.",
    )
    at_risk_services: list[ServiceName] = Field(
        default_factory=list,
        max_length=15,
        description="Downstream services that depend on an affected service and are not yet degraded.",
    )
    blast_radius: str = Field(
        min_length=20,
        max_length=500,
        description="Technical statement of how far this reaches: what is degraded, what is next in line, and "
        "why you believe so (the dependency path).",
    )
    customer_impact: str = Field(
        min_length=20,
        max_length=300,
        description="What customers experience, in plain words, with no service names or jargon. Example: "
        "'Some customers cannot complete payment.' This is what the customer update is written from.",
    )
    evidence: list[Citation] = Field(
        min_length=1,
        max_length=8,
        description="What supports the above: kind=catalog for a service you looked up or a dependency listing "
        "you read, kind=metric ('service/metric') for a series you queried. Triage has no search or deploy "
        "tools, so no other kind is possible.",
    )

    @model_validator(mode="after")
    def _a_cascade_involves_several_services(self) -> TriageHandoff:
        if self.cascade and len(self.affected_services) < 2:
            raise ValueError("cascade is true but fewer than two services are affected; a cascade spans services")
        return self


def check_triage(output: TriageHandoff, ledger: EvidenceLedger, catalog: dict[str, ServiceEntry]) -> list[str]:
    problems = unknown_services(output.affected_services, "affected_services", catalog)
    problems += unknown_services(output.investigation_targets, "investigation_targets", catalog)
    problems += unknown_services(output.at_risk_services, "at_risk_services", catalog)
    for citation in output.evidence:
        if citation.kind not in ("catalog", "metric"):
            problems.append(f"evidence: Triage cannot cite a {citation.kind}; use catalog or metric evidence")
    return problems + ungrounded_citations(
        [c for c in output.evidence if c.kind in ("catalog", "metric")], ledger
    )


# ------------------------------------------------------------- Investigator


class Investigation(BaseModel):
    outcome: Outcome = Field(
        description="root_cause_identified: you have a hypothesis supported by cited evidence. "
        "insufficient_evidence: you could not establish a cause; say so rather than guess."
    )
    root_cause: RootCause | None = Field(
        default=None, description="Required when outcome is root_cause_identified; must be null otherwise."
    )
    evidence_gaps: list[Gap] = Field(
        default_factory=list,
        max_length=6,
        description="What is missing or contradictory. Required (at least one) when outcome is "
        "insufficient_evidence; optional caveats otherwise.",
    )
    matching_runbook: str | None = Field(
        default=None,
        description="doc_id of a retrieved runbook that actually addresses this incident, or null if none does. "
        "Null is a legitimate answer: a runbook about a different failure is not a match. Independent of "
        "outcome: you can know the cause and still have no runbook for it.",
    )
    recommended_action: str = Field(
        min_length=20,
        max_length=800,
        description="What the on-call should do next. With insufficient_evidence, say what to investigate or "
        "who to bring in.",
    )

    @model_validator(mode="after")
    def _outcome_matches_contents(self) -> Investigation:
        check_outcome_consistency(self.outcome, self.root_cause, self.evidence_gaps)
        return self


def check_investigation(
    output: Investigation, ledger: EvidenceLedger, catalog: dict[str, ServiceEntry]
) -> list[str]:
    problems: list[str] = []
    if output.root_cause:
        problems += unknown_services([output.root_cause.service], "root_cause.service", catalog)
        problems += ungrounded_citations(output.root_cause.citations, ledger)
    return problems + check_runbook(output.matching_runbook, ledger)


# --------------------------------------------------------------- Escalation

Action = Literal["page_now", "notify_business_hours", "no_action"]


class EscalationDecision(BaseModel):
    action: Action = Field(
        description="page_now: wake the on-call (you must have called page_oncall). notify_business_hours: "
        "worth a human's attention but not worth waking anyone; hand to the team's queue. no_action: nothing "
        "for a human to do now."
    )
    team: TeamName | None = Field(
        default=None,
        description="The team to page or notify, exactly as page_oncall / get_oncall report it. Required for "
        "page_now and notify_business_hours; null for no_action.",
    )
    page_id: str | None = Field(
        default=None,
        description="The page_id page_oncall returned. Required for page_now; must be null otherwise.",
    )
    reasoning: str = Field(
        min_length=20,
        max_length=600,
        description="Why this action: severity, who owns the failure, whether it is the middle of their night.",
    )
    budget_assessment: str = Field(
        min_length=10,
        max_length=400,
        description="What the error budget says (remaining, burn rate), or why you did not need to check it.",
    )

    @model_validator(mode="after")
    def _action_matches_contents(self) -> EscalationDecision:
        if self.action == "page_now" and not (self.team and self.page_id):
            raise ValueError("action is page_now but team or page_id is missing; call page_oncall and report its page_id")
        if self.action != "page_now" and self.page_id is not None:
            raise ValueError(f"page_id is set but action is {self.action}; page_id is only for page_now")
        if self.action == "notify_business_hours" and not self.team:
            raise ValueError("action is notify_business_hours but team is missing")
        return self


def check_escalation(
    output: EscalationDecision, ledger: EvidenceLedger, catalog: dict[str, ServiceEntry]
) -> list[str]:
    """The decision must describe what actually happened: a page the agent
    made must be reported, and a page it reports must exist."""
    problems: list[str] = []
    if ledger.pages and output.action != "page_now":
        problems.append(
            f"you paged ({', '.join(ledger.pages)}) but action is {output.action}; report what you did: action=page_now "
            f"with that page_id"
        )
    if output.action == "page_now":
        if output.page_id not in ledger.pages:
            problems.append(
                f"page_id '{output.page_id}' was not returned by page_oncall in this investigation"
                + (f"; the page you made is {list(ledger.pages)}" if ledger.pages else "; you have not paged anyone")
            )
        elif ledger.pages[output.page_id] != output.team:
            problems.append(
                f"team is '{output.team}' but page {output.page_id} went to '{ledger.pages[output.page_id]}'; "
                f"use the team page_oncall returned"
            )
    elif output.team and output.team not in ledger.oncall_teams:
        problems.append(f"team '{output.team}' was never looked up; call get_oncall for it first")
    if len(ledger.pages) > 1:
        problems.append(f"you made {len(ledger.pages)} pages for one incident; page at most once")
    return problems


# -------------------------------------------------------------------- Comms

_SEVERITY_LABEL = re.compile(r"\bSEV[ -]?[1-4]\b", re.IGNORECASE)
_DOC_ID = re.compile(r"\b(?:runbook|postmortem|alert|chat|catalog)-[a-z0-9_-]+", re.IGNORECASE)


class CustomerUpdate(BaseModel):
    headline: str = Field(min_length=10, max_length=120, description="One line a customer can understand at a glance.")
    customer_impact: str = Field(
        min_length=20,
        max_length=400,
        description="First thing the reader learns: who is affected and how, in plain words.",
    )
    status: Literal["investigating", "identified"] = Field(
        description="investigating: the cause is not established. identified: the investigation found a cause "
        "(only allowed if it did)."
    )
    confirmed: list[Annotated[str, Field(min_length=10, max_length=200)]] = Field(
        min_length=1,
        max_length=5,
        description="Facts that are established: what customers experience, what is known. Nothing speculative.",
    )
    suspected: list[Annotated[str, Field(min_length=10, max_length=200)]] = Field(
        default_factory=list,
        max_length=3,
        description="Hypotheses, worded as hypotheses ('we believe'). Must be empty if the investigation could "
        "not establish a cause.",
    )
    what_we_are_doing: str = Field(
        min_length=20, max_length=300, description="What is being done now, without promising a fix time."
    )
    next_update_minutes: int = Field(ge=5, le=240, description="Minutes until the next update.")

    def texts(self) -> list[str]:
        return [self.headline, self.customer_impact, *self.confirmed, *self.suspected, self.what_we_are_doing]


def internal_terms(text: str, catalog: dict[str, ServiceEntry]) -> list[str]:
    """Internal identifiers that must not appear in customer-facing text."""
    found = [
        name
        for name in catalog
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text, re.IGNORECASE)
    ]
    found += [m.group(0) for m in _SEVERITY_LABEL.finditer(text)]
    found += [m.group(0) for m in _DOC_ID.finditer(text)]
    return found


def comms_check(investigation: Investigation):
    """Comms has no tools and so no evidence to ground against; what it can be
    held to is its inputs: no internal jargon, and no claiming more than the
    Investigator found."""

    def check(output: CustomerUpdate, ledger: EvidenceLedger, catalog: dict[str, ServiceEntry]) -> list[str]:
        problems = []
        leaked = sorted({term for text in output.texts() for term in internal_terms(text, catalog)})
        if leaked:
            problems.append(
                f"customer-facing text contains internal terms {leaked}; describe them in plain words "
                f"customers would use (the triage customer_impact field shows how)"
            )
        if investigation.outcome == "insufficient_evidence":
            if output.status == "identified":
                problems.append("status is identified but the investigation found no cause; use investigating")
            if output.suspected:
                problems.append("suspected must be empty: the investigation could not establish any cause")
        return problems

    return check


# ------------------------------------------------------------ output specs

TRIAGE_SPEC = OutputSpec(
    tool_name="submit_triage",
    description=(
        "Submit your triage: severity, who is affected, where the root cause most likely lives, and what customers "
        "experience. Call exactly once, when you have established the blast radius. Ends your work and hands "
        "this to the Investigator, who will look where you point, so investigation_targets matters most. "
        "Evidence must come from your own tool calls. Do not call this to ask a question."
    ),
    model=TriageHandoff,
    check=check_triage,
    fallback_hint="your best-supported severity, noting uncertainty in severity_rationale",
)

INVESTIGATION_SPEC = OutputSpec(
    tool_name="submit_investigation",
    description=(
        "Submit your investigation: the probable root cause with cited evidence, or outcome=insufficient_evidence "
        "when the evidence does not support one. Call exactly once. Ends your work and hands this to Escalation "
        "and Comms. Every citation must refer to evidence your own tool calls returned; anything else is "
        "rejected. Do not call this to report progress."
    ),
    model=Investigation,
    check=check_investigation,
)

ESCALATION_SPEC = OutputSpec(
    tool_name="submit_escalation",
    description=(
        "Submit your paging decision. Call exactly once, after you have either paged (page_oncall) or decided "
        "not to. Your decision must match what you did: if you paged, report action=page_now with the page_id "
        "page_oncall returned. Ends your work and hands the decision to Comms."
    ),
    model=EscalationDecision,
    check=check_escalation,
    fallback_hint="action=no_action or notify_business_hours, whichever the severity supports",
)


def comms_spec(investigation: Investigation) -> OutputSpec:
    return OutputSpec(
        tool_name="submit_update",
        description=(
            "Submit the customer-facing status update. Call exactly once. Write only from the handoffs you were "
            "given; you have no way to look anything up. Customer-facing text must contain no service names, "
            "severity labels or document ids; an update that does is rejected."
        ),
        model=CustomerUpdate,
        check=comms_check(investigation),
        fallback_hint="status=investigating with only what is confirmed",
    )


# ----------------------------------------------------------- final packet


class IncidentPacket(BaseModel):
    """The pipeline's complete output: everything the four agents produced."""

    incident_id: str | None
    status: Literal["completed", "partial"]
    triage: TriageHandoff
    investigation: Investigation
    investigation_source: Literal["agent", "system_fallback"] = "agent"
    escalation: EscalationDecision | None = None
    customer_update: CustomerUpdate | None = None
