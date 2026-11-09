import json

import pytest
from pydantic import ValidationError

from meridian.agent.evidence import EvidenceLedger
from meridian.multiagent.schemas import (
    ESCALATION_SPEC,
    INVESTIGATION_SPEC,
    TRIAGE_SPEC,
    CustomerUpdate,
    EscalationDecision,
    Investigation,
    TriageHandoff,
    check_escalation,
    check_investigation,
    check_triage,
    comms_spec,
    internal_terms,
)


def triage(**overrides):
    base = {
        "severity": "SEV2",
        "severity_rationale": "A tier-1 service is partly degraded.",
        "cascade": False,
        "affected_services": ["checkout-api"],
        "investigation_targets": ["postgres-primary"],
        "blast_radius": "Checkout is degraded; services that depend on it are next in line.",
        "customer_impact": "Some customers cannot complete a purchase.",
        "evidence": [{"kind": "catalog", "ref": "checkout-api", "supports": "the alerting service was looked up"}],
    }
    return {**base, **overrides}


def investigation(**overrides):
    base = {
        "outcome": "insufficient_evidence",
        "evidence_gaps": ["Nothing retrieved describes this failure."],
        "recommended_action": "Ask the owning team to inspect the service directly.",
    }
    return {**base, **overrides}


def escalation(**overrides):
    base = {
        "action": "notify_business_hours",
        "team": "data-platform",
        "reasoning": "Severity two with a healthy budget; it can wait for business hours.",
        "budget_assessment": "Budget remaining is healthy.",
    }
    return {**base, **overrides}


def update(**overrides):
    base = {
        "headline": "Some customers are seeing errors",
        "customer_impact": "Some customers may see errors while browsing or buying right now.",
        "status": "investigating",
        "confirmed": ["Some customers are seeing errors at the moment."],
        "what_we_are_doing": "Our engineers are working to find the cause right now.",
        "next_update_minutes": 30,
    }
    return {**base, **overrides}


def ledger(**kwargs):
    ledger = EvidenceLedger()
    ledger.services.update(kwargs.get("services", []))
    ledger.metrics.update(kwargs.get("metrics", []))
    ledger.pages.update(kwargs.get("pages", {}))
    ledger.oncall_teams.update(kwargs.get("teams", []))
    return ledger


# ------------------------------------------------------------------- Triage


def test_a_valid_triage_handoff_parses():
    assert TriageHandoff.model_validate(triage()).investigation_targets == ["postgres-primary"]


def test_a_cascade_must_span_services():
    with pytest.raises(ValidationError, match="fewer than two"):
        TriageHandoff.model_validate(triage(cascade=True))
    assert TriageHandoff.model_validate(triage(cascade=True, affected_services=["checkout-api", "cart-service"]))


@pytest.mark.parametrize(
    "overrides",
    [
        {"investigation_targets": []},
        {"affected_services": []},
        {"evidence": []},
        {"severity": "SEV0"},
        {"customer_impact": "bad"},
    ],
)
def test_incomplete_triage_handoffs_are_rejected(overrides):
    with pytest.raises(ValidationError):
        TriageHandoff.model_validate(triage(**overrides))


def test_triage_services_are_normalised():
    handoff = TriageHandoff.model_validate(triage(investigation_targets=[" Postgres-Primary "]))

    assert handoff.investigation_targets == ["postgres-primary"]


def test_triage_cannot_cite_what_it_has_no_tools_to_retrieve(s_catalog):
    bad = triage(evidence=[{"kind": "document", "ref": "runbook-x", "supports": "a runbook says so, apparently"}])

    problems = check_triage(TriageHandoff.model_validate(bad), ledger(), s_catalog)

    assert any("cannot cite a document" in p for p in problems)


def test_triage_evidence_and_services_are_checked(s_catalog):
    good = TriageHandoff.model_validate(triage())
    assert check_triage(good, ledger(services=["checkout-api"]), s_catalog) == []
    assert len(check_triage(good, ledger(), s_catalog)) == 1  # the catalog lookup never happened

    unknown = TriageHandoff.model_validate(triage(investigation_targets=["postgres-primry"], at_risk_services=["ghost"]))
    problems = check_triage(unknown, ledger(services=["checkout-api"]), s_catalog)
    assert len(problems) == 2 and "Did you mean" in problems[0]


# ------------------------------------------------------------ Investigation


def test_investigation_keeps_diagnosed_and_unknown_distinct():
    assert Investigation.model_validate(investigation())
    with pytest.raises(ValidationError, match="root_cause is missing"):
        Investigation.model_validate(investigation(outcome="root_cause_identified"))
    with pytest.raises(ValidationError, match="evidence_gaps is empty"):
        Investigation.model_validate(investigation(evidence_gaps=[]))
    cause = {
        "service": "postgres-primary", "category": "disk_full", "confidence": "high",
        "summary": "The data volume filled up and writes are refused.",
        "citations": [{"kind": "metric", "ref": "postgres-primary/disk_used_percent", "supports": "disk usage reached 100 percent"}],
    }
    with pytest.raises(ValidationError, match="root_cause is set"):
        Investigation.model_validate(investigation(root_cause=cause))


def test_investigation_citations_are_grounded_in_its_own_retrievals(s_catalog):
    cause = {
        "service": "postgres-primary", "category": "disk_full", "confidence": "high",
        "summary": "The data volume filled up and writes are refused.",
        "citations": [{"kind": "metric", "ref": "postgres-primary/disk_used_percent", "supports": "disk usage reached 100 percent"}],
    }
    report = Investigation.model_validate(investigation(outcome="root_cause_identified", evidence_gaps=[], root_cause=cause))

    assert check_investigation(report, ledger(metrics=["postgres-primary/disk_used_percent"]), s_catalog) == []
    assert len(check_investigation(report, ledger(), s_catalog)) == 1


# --------------------------------------------------------------- Escalation


def test_escalation_actions_require_their_fields():
    assert EscalationDecision.model_validate(escalation())
    assert EscalationDecision.model_validate(escalation(action="no_action", team=None))
    assert EscalationDecision.model_validate(escalation(action="page_now", page_id="sim-page-0001"))
    with pytest.raises(ValidationError, match="page_id is missing"):
        EscalationDecision.model_validate(escalation(action="page_now"))
    with pytest.raises(ValidationError, match="only for page_now"):
        EscalationDecision.model_validate(escalation(page_id="sim-page-0001"))
    with pytest.raises(ValidationError, match="team is missing"):
        EscalationDecision.model_validate(escalation(team=None))


def test_a_page_the_agent_made_must_be_reported(s_catalog):
    decision = EscalationDecision.model_validate(escalation(action="no_action", team=None))

    problems = check_escalation(decision, ledger(pages={"sim-page-0001": "data-platform"}), s_catalog)

    assert len(problems) == 1 and "you paged" in problems[0] and "sim-page-0001" in problems[0]


def test_a_page_the_agent_reports_must_exist(s_catalog):
    decision = EscalationDecision.model_validate(escalation(action="page_now", page_id="sim-page-9999"))

    never = check_escalation(decision, ledger(), s_catalog)
    wrong = check_escalation(decision, ledger(pages={"sim-page-0001": "data-platform"}), s_catalog)

    assert "you have not paged anyone" in never[0]
    assert "sim-page-0001" in wrong[0]


def test_the_reported_team_must_be_the_team_that_was_paged(s_catalog):
    decision = EscalationDecision.model_validate(escalation(action="page_now", page_id="sim-page-0001", team="edge-platform"))

    problems = check_escalation(decision, ledger(pages={"sim-page-0001": "data-platform"}), s_catalog)

    assert len(problems) == 1 and "data-platform" in problems[0]
    ok = EscalationDecision.model_validate(escalation(action="page_now", page_id="sim-page-0001"))
    assert check_escalation(ok, ledger(pages={"sim-page-0001": "data-platform"}), s_catalog) == []


def test_a_team_to_notify_must_have_been_looked_up(s_catalog):
    decision = EscalationDecision.model_validate(escalation())

    assert "get_oncall" in check_escalation(decision, ledger(), s_catalog)[0]
    assert check_escalation(decision, ledger(teams=["data-platform"]), s_catalog) == []


def test_one_incident_gets_at_most_one_page(s_catalog):
    decision = EscalationDecision.model_validate(escalation(action="page_now", page_id="sim-page-0001"))

    problems = check_escalation(decision, ledger(pages={"sim-page-0001": "data-platform", "sim-page-0002": "data-platform"}), s_catalog)

    assert any("2 pages" in p for p in problems)


# -------------------------------------------------------------------- Comms


def test_a_valid_update_parses_and_is_bounded():
    assert CustomerUpdate.model_validate(update())
    for bad in ({"next_update_minutes": 1}, {"next_update_minutes": 999}, {"confirmed": []}, {"status": "fixed"}, {"headline": "short"}):
        with pytest.raises(ValidationError):
            CustomerUpdate.model_validate(update(**bad))


@pytest.mark.parametrize(
    "text, expected",
    [
        ("We are investigating checkout-api errors", ["checkout-api"]),
        ("CHECKOUT-API and postgres-primary are affected", ["checkout-api", "postgres-primary"]),
        ("This is a SEV2 incident", ["SEV2"]),
        ("a sev 1 situation", ["sev 1"]),
        ("see runbook-postgres-connection-pool for details", ["runbook-postgres-connection-pool"]),
        ("Customers cannot check out or sign in", []),
        ("Our checkout is slow", []),
        ("the checkout-api-v2 beta", []),  # a different identifier, not a catalog service
    ],
)
def test_internal_terms_are_found_in_customer_text(s_catalog, text, expected):
    assert [t for t in internal_terms(text, s_catalog)] == expected


def test_the_update_check_rejects_internal_jargon_anywhere_in_the_update(s_catalog):
    spec = comms_spec(Investigation.model_validate(investigation(outcome="insufficient_evidence")))
    for field, value in (
        ("headline", "Problems with checkout-api today"),
        ("what_we_are_doing", "Engineers are restarting postgres-primary now."),
        ("confirmed", ["This is a SEV1 incident for customers."]),
    ):
        report = CustomerUpdate.model_validate(update(**{field: value}))
        problems = spec.check(report, EvidenceLedger(), s_catalog)
        assert len(problems) == 1 and "internal terms" in problems[0], field
    assert spec.check(CustomerUpdate.model_validate(update()), EvidenceLedger(), s_catalog) == []


def test_comms_cannot_claim_more_than_the_investigator_found(s_catalog):
    unknown = comms_spec(Investigation.model_validate(investigation()))
    claims_cause = CustomerUpdate.model_validate(update(status="identified"))
    guesses = CustomerUpdate.model_validate(update(suspected=["We believe a database problem is to blame."]))

    assert "no cause" in unknown.check(claims_cause, EvidenceLedger(), s_catalog)[0]
    assert "suspected must be empty" in unknown.check(guesses, EvidenceLedger(), s_catalog)[0]

    cause = {
        "service": "postgres-primary", "category": "disk_full", "confidence": "high",
        "summary": "The data volume filled up and writes are refused.",
        "citations": [{"kind": "metric", "ref": "postgres-primary/disk_used_percent", "supports": "disk usage reached 100 percent"}],
    }
    known = comms_spec(Investigation.model_validate(investigation(outcome="root_cause_identified", evidence_gaps=[], root_cause=cause)))
    assert known.check(claims_cause, EvidenceLedger(), s_catalog) == []
    assert known.check(guesses, EvidenceLedger(), s_catalog) == []


# -------------------------------------------------------------- output specs


def test_each_agent_has_its_own_submit_tool_with_a_self_contained_described_schema():
    specs = [TRIAGE_SPEC, INVESTIGATION_SPEC, ESCALATION_SPEC, comms_spec(Investigation.model_validate(investigation()))]

    assert [s.tool_name for s in specs] == ["submit_triage", "submit_investigation", "submit_escalation", "submit_update"]
    for spec in specs:
        schema = spec.tool_schema()
        assert "$ref" not in json.dumps(schema) and len(schema["description"]) > 120
        undescribed = [n for n, p in schema["input_schema"]["properties"].items() if "description" not in p]
        assert undescribed == [], spec.tool_name
