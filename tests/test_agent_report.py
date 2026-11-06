import json

import jsonschema
import pytest
from pydantic import ValidationError

from meridian.agent.evidence import EvidenceLedger
from meridian.agent.report import (
    Category,
    IncidentReport,
    check_report,
    format_validation_error,
    report_input_schema,
    submit_tool_schema,
)
from meridian.corpus.taxonomy import CATEGORY_INFO


def citation(**overrides):
    return {"kind": "catalog", "ref": "checkout-api", "supports": "checkout-api is the alerting service", **overrides}


def diagnosis(**overrides):
    base = {
        "severity": "SEV2",
        "severity_rationale": "A tier-1 service is partly degraded.",
        "affected_services": ["checkout-api"],
        "outcome": "root_cause_identified",
        "root_cause": {
            "service": "postgres-primary",
            "category": "connection_pool_exhaustion",
            "summary": "The connection pool is saturated and requests are queueing.",
            "confidence": "medium",
            "citations": [citation()],
        },
        "recommended_action": "Raise the pool size and watch pool utilisation recover.",
    }
    return {**base, **overrides}


def unknown(**overrides):
    base = {
        "severity": "SEV3",
        "severity_rationale": "Limited impact observed.",
        "affected_services": ["checkout-api"],
        "outcome": "insufficient_evidence",
        "evidence_gaps": ["No metric deviated and no retrieved document describes this failure."],
        "recommended_action": "Ask the owning team to check application logs for the failing job.",
    }
    return {**base, **overrides}


# ------------------------------------------------------------------ shape


def test_a_diagnosis_parses():
    report = IncidentReport.model_validate(diagnosis())

    assert report.outcome == "root_cause_identified"
    assert report.root_cause.service == "postgres-primary"


def test_an_insufficient_evidence_report_parses_without_a_hypothesis():
    report = IncidentReport.model_validate(unknown())

    assert report.root_cause is None and report.evidence_gaps


def test_a_diagnosis_must_carry_a_root_cause():
    with pytest.raises(ValidationError, match="root_cause is missing"):
        IncidentReport.model_validate(diagnosis(root_cause=None))


def test_insufficient_evidence_must_not_smuggle_in_a_hypothesis():
    with pytest.raises(ValidationError, match="root_cause is set"):
        IncidentReport.model_validate(unknown(root_cause=diagnosis()["root_cause"]))


def test_insufficient_evidence_must_say_what_is_missing():
    with pytest.raises(ValidationError, match="evidence_gaps is empty"):
        IncidentReport.model_validate(unknown(evidence_gaps=[]))


def test_a_hypothesis_needs_at_least_one_citation():
    bad = diagnosis()
    bad["root_cause"]["citations"] = []

    with pytest.raises(ValidationError, match="at least 1"):
        IncidentReport.model_validate(bad)


@pytest.mark.parametrize(
    "overrides",
    [
        {"severity": "SEV5"},
        {"severity": "sev2"},
        {"affected_services": []},
        {"outcome": "probably"},
        {"recommended_action": "fix it"},
    ],
)
def test_malformed_reports_are_rejected(overrides):
    with pytest.raises(ValidationError):
        IncidentReport.model_validate(diagnosis(**overrides))


def test_service_names_are_normalised_like_tool_arguments():
    report = IncidentReport.model_validate(diagnosis(affected_services=[" Checkout-API "]))

    assert report.affected_services == ["checkout-api"]


def test_every_category_a_scenario_can_have_is_a_valid_category(s_scenarios):
    options = set(Category.__args__)

    assert {s.category for s in s_scenarios.values()} <= options
    assert {"connection_pool_exhaustion", "deploy_regression", "other"} <= options
    assert set(CATEGORY_INFO) < options


def test_validation_errors_are_formatted_for_the_model():
    with pytest.raises(ValidationError) as caught:
        IncidentReport.model_validate({"severity": "SEV9"})

    message = format_validation_error(caught.value)

    assert "severity:" in message and "affected_services:" in message
    assert "SEV9" not in message  # the offending input is not echoed back


# ------------------------------------------------------------ tool schema


def test_the_submit_schema_is_self_contained():
    schema = submit_tool_schema()

    assert schema["name"] == "submit_report"
    assert "$ref" not in json.dumps(schema) and "$defs" not in json.dumps(schema)
    assert set(schema["input_schema"]["required"]) == {
        "severity", "severity_rationale", "affected_services", "outcome", "recommended_action",
    }
    assert schema["input_schema"]["properties"]["severity"]["enum"] == ["SEV1", "SEV2", "SEV3", "SEV4"]
    assert len(schema["description"]) > 150  # the model chooses this tool by its description


def test_the_published_schema_accepts_what_the_model_accepts_and_rejects_obvious_garbage():
    schema = report_input_schema()

    jsonschema.validate(diagnosis(), schema)
    jsonschema.validate(unknown(), schema)
    for bad in (diagnosis(severity="SEV5"), {"severity": "SEV1"}, diagnosis(affected_services=[])):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_every_field_in_the_schema_is_described_for_the_model():
    props = report_input_schema()["properties"]

    undescribed = [name for name, p in props.items() if "description" not in p]
    assert undescribed == []


# --------------------------------------------------------------- grounding


def ledger_with(**kwargs):
    ledger = EvidenceLedger()
    ledger.documents.update(kwargs.get("documents", {}))
    ledger.services.update(kwargs.get("services", []))
    ledger.deploys.update(kwargs.get("deploys", []))
    ledger.metrics.update(kwargs.get("metrics", []))
    return ledger


def test_a_grounded_report_has_no_problems(s_catalog):
    report = IncidentReport.model_validate(diagnosis())

    assert check_report(report, ledger_with(services=["checkout-api"]), s_catalog) == []


def test_a_citation_the_agent_never_retrieved_is_rejected(s_catalog):
    bad = diagnosis()
    bad["root_cause"]["citations"] = [citation(kind="document", ref="runbook-i-made-this-up")]

    problems = check_report(IncidentReport.model_validate(bad), ledger_with(), s_catalog)

    assert len(problems) == 1 and "runbook-i-made-this-up" in problems[0]


@pytest.mark.parametrize(
    "kind, ref, ledger",
    [
        ("document", "runbook-x", {"documents": {"runbook-x": "runbook"}}),
        ("deploy", "dep-a-1", {"deploys": ["dep-a-1"]}),
        ("metric", "checkout-api/error_rate", {"metrics": ["checkout-api/error_rate"]}),
        ("catalog", "Checkout-API", {"services": ["checkout-api"]}),
    ],
)
def test_each_citation_kind_is_checked_against_its_own_evidence(s_catalog, kind, ref, ledger):
    bad = diagnosis()
    bad["root_cause"]["citations"] = [citation(kind=kind, ref=ref)]
    report = IncidentReport.model_validate(bad)

    assert check_report(report, ledger_with(**ledger), s_catalog) == []
    assert len(check_report(report, ledger_with(), s_catalog)) == 1


def test_a_citation_of_the_wrong_kind_does_not_match(s_catalog):
    bad = diagnosis()
    bad["root_cause"]["citations"] = [citation(kind="deploy", ref="runbook-x")]

    assert check_report(IncidentReport.model_validate(bad), ledger_with(documents={"runbook-x": "runbook"}), s_catalog)


def test_services_must_exist_and_a_near_miss_gets_a_suggestion(s_catalog):
    report = IncidentReport.model_validate(diagnosis(affected_services=["checkout-apii"]))

    problems = check_report(report, ledger_with(services=["checkout-api"]), s_catalog)

    assert len(problems) == 1 and "checkout-api" in problems[0] and "Did you mean" in problems[0]


def test_matching_runbook_must_be_a_retrieved_runbook_not_a_postmortem(s_catalog):
    seen = ledger_with(documents={"postmortem-a": "postmortem", "runbook-a": "runbook"}, services=["checkout-api"])

    assert check_report(IncidentReport.model_validate(unknown(matching_runbook="runbook-a")), seen, s_catalog) == []
    wrong_type = check_report(IncidentReport.model_validate(unknown(matching_runbook="postmortem-a")), seen, s_catalog)
    never_seen = check_report(IncidentReport.model_validate(unknown(matching_runbook="runbook-b")), seen, s_catalog)
    assert "not a runbook" in wrong_type[0]
    assert "not returned by any search" in never_seen[0]


def test_the_ledger_records_only_what_tools_actually_return(agent_env):
    env = agent_env()
    ledger = EvidenceLedger()
    for name, args in (
        ("search_runbooks", {"query": "elevated error rate", "k": 3}),
        ("get_deploy_history", {"service": env.scenario.root_cause_service, "window": "24h"}),
        ("query_metrics", {"service": env.scenario.root_cause_service, "metric": "error_rate"}),
        ("get_dependents", {"name": env.scenario.root_cause_service}),
    ):
        ledger.record(name, args, env.toolset.call(name, args))

    assert ledger.documents and all(t == "runbook" for t in ledger.documents.values())
    assert ledger.has("metric", f"{env.scenario.root_cause_service}/error_rate")
    assert not ledger.has("metric", f"{env.scenario.root_cause_service}/latency_p99_ms")
    dependents = env.toolset.call("get_dependents", {"name": env.scenario.root_cause_service})["services"]
    assert dependents and all(ledger.has("catalog", d["name"]) for d in dependents)
    assert not ledger.has("document", "runbook-never-returned")
