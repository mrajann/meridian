import json
import re

import pytest

from meridian.agent import SYSTEM_PROMPT
from meridian.agent.__main__ import _pick
from meridian.agent.__main__ import main as cli_main
from meridian.agent.scripted import RoutedClient, ScriptedClient, reply, tool_use
from meridian.agent.session import IncidentSession
from meridian.agent.trace import PipelineTrace, RunTrace
from meridian.config import Settings
from meridian.indexing.__main__ import main as index_main
from meridian.multiagent import compare, prompts
from meridian.multiagent.compare import RunSummary, run_architecture, score


def single_steps(env):
    root = env.scenario.root_cause_service
    report = {
        "severity": "SEV3", "severity_rationale": "Impact looks limited.", "affected_services": [root],
        "outcome": "insufficient_evidence", "evidence_gaps": ["Nothing retrieved describes this failure."],
        "recommended_action": "Ask the owning team to inspect the service directly.",
    }
    return [reply(tool_use("get_service", {"name": root})), reply(tool_use("submit_report", report))]


def session_of(env):
    return IncidentSession(env.alert, env.scenario, env.ctx, env.catalog)


# ------------------------------------------------------------ both paths run


def test_the_single_agent_from_increment_7_still_runs_unchanged(agent_env):
    env = agent_env()

    summary, trace = run_architecture("single", session_of(env), ScriptedClient(*single_steps(env)))

    assert isinstance(trace, RunTrace) and trace.agent == "single-agent" and trace.system_prompt_sha
    assert (summary.architecture, summary.status, summary.agents) == ("single", "completed", 1)
    assert summary.outcome == "insufficient_evidence" and summary.escalation_action is None


def test_the_single_agent_is_offered_all_eleven_tools_not_a_subset(agent_env):
    env = agent_env()
    client = ScriptedClient(*single_steps(env))

    run_architecture("single", session_of(env), client)

    assert [t["name"] for t in client.requests[0]["tools"]][:11] == [
        "search_runbooks", "search_postmortems", "find_similar_incidents", "get_service", "get_dependencies",
        "get_dependents", "query_metrics", "get_deploy_history", "compute_error_budget", "get_oncall", "page_oncall",
    ]
    assert client.requests[0]["system"] == SYSTEM_PROMPT


def test_the_multi_agent_path_returns_a_pipeline_trace_and_a_summary_of_the_same_shape(agent_env, ma):
    env = agent_env()

    summary, trace = run_architecture("multi", session_of(env), ma.client(env))

    assert isinstance(trace, PipelineTrace)
    assert (summary.architecture, summary.status, summary.agents) == ("multi", "completed", 4)
    assert summary.escalation_action == "notify_business_hours" and summary.customer_headline
    assert summary.severity == "SEV2" and summary.model_calls == 7


def test_both_architectures_report_the_same_fields_for_comparison(agent_env, ma):
    env = agent_env()
    single, _ = run_architecture("single", session_of(env), ScriptedClient(*single_steps(env)))
    multi, _ = run_architecture("multi", session_of(env).fresh(), ma.client(env))

    assert set(single.__dict__) == set(multi.__dict__) == set(RunSummary.__dataclass_fields__)
    for summary in (single, multi):
        assert summary.incident_id == env.incident_id
        assert summary.input_tokens > 0 and summary.output_tokens > 0 and summary.duration_ms > 0
        assert summary.tool_calls >= 2 and summary.tool_errors == 0


def test_a_fresh_session_has_its_own_pager_so_runs_do_not_see_each_others_pages(agent_env):
    session = session_of(agent_env())
    again = session.fresh()

    assert again.ctx.pager is not session.ctx.pager and again.scenario is session.scenario
    assert again.alert is session.alert and again.ctx.telemetry is not session.ctx.telemetry


def test_an_unknown_architecture_is_refused(agent_env):
    with pytest.raises(ValueError, match="unknown architecture"):
        run_architecture("swarm", session_of(agent_env()), ScriptedClient())


def test_a_failed_run_is_summarised_not_raised(agent_env, ma):
    env = agent_env()

    def down(_):
        raise ConnectionError("down")

    single, _ = run_architecture("single", session_of(env), ScriptedClient(down))
    multi, _ = run_architecture("multi", session_of(env).fresh(), ma.client(env, triage=[down]))

    assert (single.status, single.failure, single.severity) == ("failed", "api_error", None)
    assert (multi.status, multi.failure, multi.severity) == ("failed", "triage: api_error", None)


# ------------------------------------------------------------------- scoring


def summary_with(env, **overrides):
    fields = dict(
        architecture="single", incident_id=env.incident_id, status="completed", failure=None, severity="SEV2",
        affected_services=[], outcome="root_cause_identified", root_cause_service=None, root_cause_category=None,
        confidence="high", matching_runbook=None, recommended_action=None, escalation_action=None, pages_made=0,
        customer_headline=None, agents=1, model_calls=1, tool_calls=1, tool_errors=0, input_tokens=1,
        output_tokens=1, duration_ms=1.0,
    )
    return RunSummary(**{**fields, **overrides})


def test_scoring_checks_the_diagnosis_against_the_synthetic_worlds_truth(agent_env):
    env = agent_env()
    truth = env.scenario
    session = session_of(env)

    right = score(summary_with(env, root_cause_service=truth.root_cause_service, root_cause_category=truth.category), session)
    wrong = score(summary_with(env, root_cause_service="not-the-service", root_cause_category="other"), session)
    abstained = score(summary_with(env, outcome="insufficient_evidence"), session)

    assert (right.root_cause_service_correct, right.root_cause_category_correct) == (True, True)
    assert (wrong.root_cause_service_correct, wrong.root_cause_category_correct) == (False, False)
    assert (abstained.root_cause_service_correct, abstained.root_cause_category_correct) == (False, False)


def test_runbook_scoring_rewards_the_right_runbook_or_correctly_finding_none(agent_env, s_documents):
    with_runbook = next(d for d in s_documents if d.doc_type == "alert" and d.metadata.get("has_matching_runbook"))
    without = next(d for d in s_documents if d.doc_type == "alert" and not d.metadata.get("has_matching_runbook"))

    for alert, good, bad in (
        (with_runbook, with_runbook.metadata["correct_runbook"], None),
        (without, None, "runbook-something-else"),
    ):
        env = agent_env(alert.doc_id)
        session = session_of(env)
        assert score(summary_with(env, matching_runbook=good), session).runbook_correct
        assert not score(summary_with(env, matching_runbook=bad), session).runbook_correct
        assert not score(summary_with(env, matching_runbook=good, status="failed"), session).runbook_correct


def test_as_dict_flattens_summary_and_score(agent_env):
    env = agent_env()
    row = compare.as_dict(summary_with(env), score(summary_with(env), session_of(env)))

    assert row["incident_id"] == env.incident_id and "score_root_cause_service_correct" in row


# ------------------------------------------------------------------------ CLI


@pytest.fixture
def cli(tmp_path, monkeypatch):
    settings = Settings(embedding_backend="hashing", chroma_persist_dir=tmp_path / "chroma", anthropic_api_key="sk-test", _env_file=None)
    monkeypatch.setattr("meridian.indexing.__main__.settings", settings)
    monkeypatch.setattr("meridian.agent.__main__.settings", settings)
    index_main(["build"])
    return settings


def first_service(request):
    return re.search(r"Services named in the alert: ([a-z0-9-]+)", request["messages"][0]["content"]).group(1)


def generic_client(runs: int):
    """A client for `runs` incident runs of each architecture, deriving everything it
    submits from the task text, so one script serves any incident."""
    root = lambda r: first_service(r)
    ca = lambda name: lambda r: reply(tool_use("get_service", {"name": root(r)}))
    triage = [ca("t"), lambda r: reply(tool_use("submit_triage", {
        "severity": "SEV2", "severity_rationale": "A tier-1 service is partly degraded.", "cascade": False,
        "affected_services": [root(r)], "investigation_targets": [root(r)],
        "blast_radius": "The service and what depends on it are degraded.",
        "customer_impact": "Some customers see errors when browsing or buying.",
        "evidence": [{"kind": "catalog", "ref": root(r), "supports": "the alerting service was looked up"}]}))]
    investigator = [lambda r: reply(tool_use("submit_investigation", {
        "outcome": "insufficient_evidence", "evidence_gaps": ["Nothing retrieved describes this failure."],
        "recommended_action": "Ask the owning team to inspect the service directly."}))]
    escalation = [
        ca("e"),
        lambda r: reply(tool_use("get_oncall", {"team": json.loads(r["messages"][-1]["content"][0]["content"])["owner"]})),
        lambda r: reply(tool_use("submit_escalation", {
            "action": "notify_business_hours", "team": json.loads(r["messages"][-1]["content"][0]["content"])["team"],
            "reasoning": "Severity two with a healthy budget; it can wait.", "budget_assessment": "Budget is healthy."})),
    ]
    comms = [lambda r: reply(tool_use("submit_update", {
        "headline": "Some customers are seeing errors", "customer_impact": "Some customers may see errors while browsing or buying.",
        "status": "investigating", "confirmed": ["Some customers are seeing errors right now."],
        "what_we_are_doing": "Our engineers are working to find the cause now.", "next_update_minutes": 30}))]
    single = [ca("s"), lambda r: reply(tool_use("submit_report", {
        "severity": "SEV3", "severity_rationale": "Impact looks limited.", "affected_services": [root(r)],
        "outcome": "insufficient_evidence", "evidence_gaps": ["Nothing retrieved describes this failure."],
        "recommended_action": "Ask the owning team to inspect the service directly."}))]
    scripts = {SYSTEM_PROMPT: single, prompts.TRIAGE_PROMPT: triage, prompts.INVESTIGATOR_PROMPT: investigator,
               prompts.ESCALATION_PROMPT: escalation, prompts.COMMS_PROMPT: comms}
    return RoutedClient({prompt: ScriptedClient(*(steps * runs)) for prompt, steps in scripts.items()})


INCIDENTS = ["alert-cascade-feature-flags-9", "alert-baseline-api-gateway-5xx_errors"]


def test_cli_runs_the_single_agent_by_default_and_the_pipeline_on_request(cli, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("meridian.agent.__main__.AnthropicClient", lambda key, model: generic_client(2))
    traces = tmp_path / "traces"

    for extra in ([], ["--architecture", "multi"]):
        with pytest.raises(SystemExit) as done:
            cli_main(["run", INCIDENTS[1], "--trace-dir", str(traces), *extra])
        assert done.value.code == 0

    out = capsys.readouterr().out
    assert "single-agent" in out and "triage       turn 0" in out and "comms" in out
    [single] = traces.glob("*-single-*.json")
    [multi] = traces.glob("*-multi-*.json")
    assert RunTrace.model_validate_json(single.read_text()).agent == "single-agent"
    assert len(PipelineTrace.model_validate_json(multi.read_text()).agents) == 4


def test_cli_compare_runs_both_architectures_on_the_same_incidents(cli, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("meridian.agent.__main__.AnthropicClient", lambda key, model: generic_client(2))
    out = tmp_path / "comparison.json"

    cli_main(["compare", "--incidents", *INCIDENTS, "--out", str(out), "--trace-dir", str(tmp_path / "traces")])

    rows = json.loads(out.read_text())
    assert [(r["incident_id"], r["architecture"]) for r in rows] == [(i, a) for i in INCIDENTS for a in ("single", "multi")]
    assert all(r["status"] == "completed" for r in rows)
    assert {r["agents"] for r in rows if r["architecture"] == "multi"} == {4}
    assert all("score_root_cause_service_correct" in r for r in rows)
    assert len(list((tmp_path / "traces").glob("*.json"))) == 4


def test_cli_compare_rejects_unknown_incidents(cli, monkeypatch):
    monkeypatch.setattr("meridian.agent.__main__.AnthropicClient", lambda key, model: generic_client(1))

    with pytest.raises(SystemExit, match="unknown incident"):
        cli_main(["compare", "--incidents", "alert-nope"])


def test_the_sample_is_evenly_spread_and_stable():
    sessions = {f"alert-{i:03d}": None for i in range(100)}
    args = type("A", (), {"incidents": None, "sample": 5})

    chosen = _pick(sessions, args)

    assert chosen == ["alert-000", "alert-020", "alert-040", "alert-060", "alert-080"]
    assert _pick(sessions, args) == chosen


def test_pages_made_counts_what_the_pager_recorded_for_both_architectures(agent_env, ma):
    env = agent_env()
    page = {"severity": "SEV2", "message": "Synthetic page: upstream failure with customer impact."}
    root = env.scenario.root_cause_service

    def page_of(request):
        for message in request["messages"]:
            if message["role"] == "user" and isinstance(message["content"], list):
                for block in message["content"]:
                    if block["type"] == "tool_result" and '"page_id"' in block["content"]:
                        return json.loads(block["content"])

    paging = [
        reply(tool_use("get_service", {"name": root})),
        lambda r: reply(tool_use("get_oncall", {"team": ma.last_result(r)["owner"]})),
        lambda r: reply(tool_use("page_oncall", {**page, "team": ma.last_result(r)["team"]})),
        lambda r: reply(tool_use("submit_escalation", ma.escalation_report(page_of(r)["team"], action="page_now", page_id=page_of(r)["page_id"]))),
    ]
    multi, _ = run_architecture("multi", session_of(env), ma.client(env, escalation=paging))
    assert (multi.pages_made, multi.escalation_action) == (1, "page_now")

    session = session_of(env).fresh()  # a second, fresh session: the single agent pages too
    team_call = lambda r: reply(tool_use("page_oncall", {**page, "team": ma.last_result(r)["team"]}))
    single_paging = [
        reply(tool_use("get_service", {"name": root})),
        lambda r: reply(tool_use("get_oncall", {"team": ma.last_result(r)["owner"]})),
        team_call,
        single_steps(env)[1],
    ]
    single, _ = run_architecture("single", session, ScriptedClient(*single_paging))
    assert single.pages_made == 1 and session_of(env).fresh().ctx.pager.records == []
