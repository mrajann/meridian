import itertools
import json

import pytest

from meridian.agent import AgentConfig, AgentLoop, RunTrace, SYSTEM_PROMPT, incident_task
from meridian.agent.loop import FINAL_TURN, NUDGE, PLACEHOLDER_TEXT, TRUNCATED
from meridian.agent.prompts import system_prompt_sha
from meridian.agent.scripted import ScriptedClient, reply, text, tool_use
from meridian.tools import TOOL_ORDER, Toolset, registered_tools
from meridian.tools.registry import Tool


def fake_clock(step: float = 0.01):
    ticks = itertools.count()
    return lambda: next(ticks) * step


def evidence_free_report(**overrides):
    """A valid report needing no retrieved evidence: the abstention path."""
    report = {
        "severity": "SEV3",
        "severity_rationale": "Impact looks limited; telemetry is quiet.",
        "affected_services": ["checkout-api"],
        "outcome": "insufficient_evidence",
        "evidence_gaps": ["No metric deviated and no document describes this failure."],
        "recommended_action": "Ask the owning team to inspect application logs for the failing path.",
    }
    return {**report, **overrides}


def submit(**overrides):
    return tool_use("submit_report", evidence_free_report(**overrides))


def diagnosis_citing(service: str, **cite):
    return {
        "severity": "SEV2",
        "severity_rationale": "A tier-1 service is partly degraded.",
        "affected_services": [service],
        "outcome": "root_cause_identified",
        "root_cause": {
            "service": service,
            "category": "other",
            "summary": "The service is failing for a reason visible in its own entry.",
            "confidence": "low",
            "citations": [{"kind": "catalog", "ref": service, "supports": "the service was looked up in the catalog", **cite}],
        },
        "recommended_action": "Follow the owning team's runbook and escalate to them.",
    }


def make_loop(env, *script, **kwargs):
    client = ScriptedClient(*script)
    loop = AgentLoop(client, env.toolset, env.catalog, clock=kwargs.pop("clock", fake_clock()), **kwargs)
    return loop, client


def run(env, *script, **kwargs):
    loop, client = make_loop(env, *script, **kwargs)
    return loop.run(incident_task(env.alert, env.scenario.now), env.incident_id), client


def tool_results_of(request):
    last = request["messages"][-1]["content"]
    return [b for b in last if b["type"] == "tool_result"]


# ------------------------------------------------------------- the happy path


def test_the_loop_runs_tools_feeds_results_back_and_returns_a_validated_report(agent_env):
    env = agent_env()
    service = env.scenario.root_cause_service
    result, client = run(
        env,
        reply(text("Checking the root."), tool_use("get_service", {"name": service})),
        reply(tool_use("submit_report", diagnosis_citing(service))),
    )

    assert result.ok and result.report.root_cause.service == service
    assert result.trace.status == "completed" and result.trace.failure_reason is None
    # round 2 saw the assistant turn echoed back, then the tool result
    second = client.requests[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    assert second[1]["content"][1]["name"] == "get_service"
    assert second[2]["content"][0]["tool_use_id"] == second[1]["content"][1]["id"]
    assert json.loads(second[2]["content"][0]["content"])["name"] == service


def test_the_model_is_offered_all_eleven_tools_plus_submit(agent_env):
    _, client = run(agent_env(), reply(submit()))

    assert [t["name"] for t in client.requests[0]["tools"]] == [*TOOL_ORDER, "submit_report"]
    assert client.requests[0]["system"] == SYSTEM_PROMPT
    assert client.requests[0]["tool_choice"] is None


def test_the_first_message_is_the_alert_without_any_ground_truth(agent_env, s_documents):
    task = incident_task(agent_env().alert, agent_env().scenario.now)

    assert agent_env().alert.title in task and "Investigate" in task
    for alert in (d for d in s_documents if d.doc_type == "alert"):
        message = incident_task(alert, agent_env().scenario.now)
        for key in ("correct_runbook", "has_matching_runbook", "adversarial_case", "root_cause_category"):
            assert key not in message
        if alert.metadata.get("correct_runbook"):
            assert alert.metadata["correct_runbook"] not in message


def test_the_system_prompt_names_no_service_or_document(s_catalog, s_documents):
    prompt = SYSTEM_PROMPT.lower()

    assert [s for s in s_catalog if s in prompt] == []
    assert [d.doc_id for d in s_documents if d.doc_id.lower() in prompt] == []
    assert [t for t in TOOL_ORDER if t not in prompt] == []  # but it does teach every tool by name
    assert "submit_report" in prompt and "insufficient_evidence" in prompt


# ------------------------------------------------------------------ parallel


def test_parallel_tool_calls_all_run_and_return_in_one_message_in_order(agent_env, valid_args):
    env = agent_env()
    args = valid_args(env.scenario)
    names = ["get_service", "query_metrics", "search_runbooks", "get_dependents"]
    calls = [tool_use(name, args[name], id=f"toolu_{i}") for i, name in enumerate(names)]

    result, client = run(env, reply(*calls), reply(submit()))

    results = tool_results_of(client.requests[1])
    assert [r["tool_use_id"] for r in results] == [f"toolu_{i}" for i in range(4)]
    assert not any(r["is_error"] for r in results)
    assert [c.name for c in result.trace.turns[0].tool_calls] == names
    assert len(client.requests[1]["messages"]) == 3  # ONE user message carries all four results


def test_all_eleven_tools_can_be_called_in_a_single_response(agent_env, valid_args):
    env = agent_env()
    calls = [tool_use(name, args) for name, args in valid_args(env.scenario).items()]

    result, client = run(env, reply(*calls), reply(submit()))

    assert len(tool_results_of(client.requests[1])) == 11
    assert [c.name for c in result.trace.calls()] == [*valid_args(env.scenario), "submit_report"]
    assert result.trace.tool_errors == 0


def test_a_submit_in_the_middle_of_parallel_calls_keeps_every_result_in_position(agent_env):
    env = agent_env()
    service = env.scenario.root_cause_service
    bad = tool_use("submit_report", evidence_free_report(severity="SEV9"), id="toolu_b")
    calls = [tool_use("get_service", {"name": service}, id="toolu_a"), bad, tool_use("get_dependents", {"name": service}, id="toolu_c")]

    _, client = run(env, reply(*calls), reply(submit()))

    results = tool_results_of(client.requests[1])
    assert [(r["tool_use_id"], r["is_error"]) for r in results] == [("toolu_a", False), ("toolu_b", True), ("toolu_c", False)]


def test_evidence_gathered_in_the_same_response_as_the_submit_counts(agent_env):
    env = agent_env()
    service = env.scenario.root_cause_service
    calls = [
        tool_use("submit_report", diagnosis_citing(service)),  # submit listed FIRST
        tool_use("get_service", {"name": service}),
    ]

    result, _ = run(env, reply(*calls))

    assert result.ok


def test_two_submits_in_one_response_accept_the_first_and_flag_the_second(agent_env):
    result, _ = run(agent_env(), reply(submit(), submit(recommended_action="A different action entirely, second.")))

    submits = result.trace.calls("submit_report")
    assert result.ok and result.report.recommended_action.startswith("Ask the owning team")
    assert [c.is_error for c in submits] == [False, True]


# --------------------------------------------------------------- tool failures


def exploding_toolset(env, secret="db password hunter2 at /srv/internal/path.py"):
    original = registered_tools()["get_service"]

    def boom(ctx, name):
        raise RuntimeError(secret)

    tools = {**registered_tools(), "get_service": Tool("get_service", boom, original.description, original.params)}
    return Toolset(env.ctx, tools)


def test_a_tool_that_raises_does_not_crash_the_run_and_the_model_is_told_generically(agent_env):
    env = agent_env()
    env.toolset = exploding_toolset(env)

    result, client = run(env, reply(tool_use("get_service", {"name": "checkout-api"})), reply(submit()))

    assert result.ok
    shown = tool_results_of(client.requests[1])[0]
    assert shown["is_error"] and "internal error" in shown["content"] and "RuntimeError" in shown["content"]
    assert "hunter2" not in shown["content"] and "/srv/internal" not in shown["content"]
    traced = result.trace.calls("get_service")[0]
    assert traced.error_kind == "internal_error" and "hunter2" in traced.error_detail  # we keep the traceback


def test_a_rejected_call_is_returned_to_the_model_as_a_tool_error(agent_env):
    result, client = run(
        agent_env(),
        reply(tool_use("get_service", {"name": "no-such-service"})),
        reply(submit()),
    )

    shown = tool_results_of(client.requests[1])[0]
    assert shown["is_error"] and "no-such-service" in shown["content"]
    call = result.trace.calls("get_service")[0]
    assert call.error_kind == "tool_error" and call.error_detail is None


@pytest.mark.parametrize(
    "name, arguments, expect",
    [
        ("get_service", {}, "missing required argument 'name'"),
        ("get_service", {"name": "checkout-api", "colour": "red"}, "unknown argument"),
        ("search_runbooks", {"query": 12345}, "invalid"),
        ("query_metrics", {"service": "checkout-api", "metric": "vibes"}, "invalid"),
        ("get_dependents", {"name": "checkout-api", "depth": "deep"}, "invalid"),
        ("get_service", "checkout-api", "must be a JSON object"),
        ("get_service", None, "must be a JSON object"),
        ("get_service", ["checkout-api"], "must be a JSON object"),
        ("teleport", {"to": "mars"}, "unknown tool"),
    ],
)
def test_malformed_arguments_come_back_as_errors_and_the_loop_continues(agent_env, name, arguments, expect):
    result, client = run(agent_env(), reply(tool_use(name, arguments)), reply(submit()))

    shown = tool_results_of(client.requests[1])[0]
    assert shown["is_error"] and expect in shown["content"]
    assert result.ok and result.trace.tool_errors == 1
    assert result.trace.calls(name)[0].arguments == arguments  # traced exactly as sent


def test_one_bad_call_does_not_stop_its_siblings(agent_env):
    calls = [tool_use("get_service", {"name": "checkout-api"}), tool_use("get_service", {}), tool_use("get_dependents", {"name": "checkout-api"})]

    _, client = run(agent_env(), reply(*calls), reply(submit()))

    assert [r["is_error"] for r in tool_results_of(client.requests[1])] == [False, True, False]


# ------------------------------------------------------------ the iteration cap


def test_the_loop_stops_at_the_iteration_cap_and_forces_a_submission_on_the_last_turn(agent_env):
    loop_script = [reply(tool_use("get_service", {"name": "checkout-api"})) for _ in range(3)]

    result, client = run(agent_env(), *loop_script, reply(submit()), config=AgentConfig(max_iterations=4))

    assert len(client.requests) == 4 and result.ok
    assert [r["tool_choice"] for r in client.requests[:3]] == [None] * 3
    assert client.requests[3]["tool_choice"] == {"type": "tool", "name": "submit_report"}
    assert FINAL_TURN in json.dumps(client.requests[3]["messages"][-1]["content"])
    assert FINAL_TURN not in json.dumps(client.requests[2]["messages"])
    assert result.trace.turns[3].forced_tool == "submit_report" and result.trace.turns[2].forced_tool is None


def test_a_model_that_never_stops_calling_tools_is_cut_off_not_looped_forever(agent_env):
    endless = [reply(tool_use("get_service", {"name": "checkout-api"})) for _ in range(5)]

    result, client = run(agent_env(), *endless, config=AgentConfig(max_iterations=5))

    assert len(client.requests) == 5  # the scripted client would raise on a sixth call
    assert not result.ok
    assert (result.trace.status, result.trace.failure_reason) == ("failed", "max_iterations")
    assert len(result.trace.turns) == 5


def test_a_single_iteration_budget_is_one_forced_submission(agent_env):
    result, client = run(agent_env(), reply(submit()), config=AgentConfig(max_iterations=1))

    assert result.ok and len(client.requests) == 1
    assert client.requests[0]["tool_choice"]["name"] == "submit_report"
    assert FINAL_TURN in client.requests[0]["messages"][0]["content"]  # appended to the task text


def test_a_rejected_report_on_the_last_turn_is_reported_as_invalid_not_as_a_timeout(agent_env):
    result, _ = run(agent_env(), reply(submit(severity="SEV9")), config=AgentConfig(max_iterations=1))

    assert (result.trace.status, result.trace.failure_reason) == ("failed", "invalid_report")


def test_the_iteration_cap_must_be_positive(agent_env):
    with pytest.raises(ValueError, match="at least 1"):
        make_loop(agent_env(), config=AgentConfig(max_iterations=0))


# ---------------------------------------------------------- report validation


def test_a_structurally_invalid_report_is_sent_back_and_the_model_can_fix_it(agent_env):
    result, client = run(
        agent_env(),
        reply(submit(severity="SEV9")),
        reply(submit()),
    )

    shown = tool_results_of(client.requests[1])[0]
    assert shown["is_error"] and "report rejected" in shown["content"] and "severity" in shown["content"]
    assert result.ok
    assert [c.is_error for c in result.trace.calls("submit_report")] == [True, False]


def test_a_citation_to_a_document_the_agent_never_saw_is_rejected(agent_env):
    env = agent_env()
    service = env.scenario.root_cause_service
    invented = diagnosis_citing(service, kind="document", ref="runbook-plausible-but-invented")

    result, client = run(env, reply(tool_use("submit_report", invented)), reply(submit()))

    shown = tool_results_of(client.requests[1])[0]
    assert shown["is_error"] and "runbook-plausible-but-invented" in shown["content"]
    assert result.report.outcome == "insufficient_evidence"


def test_a_citation_to_a_document_the_agent_did_retrieve_is_accepted(agent_env):
    env = agent_env()
    service = env.scenario.root_cause_service

    def cite_first_hit(request):
        found = json.loads(tool_results_of(request)[0]["content"])["results"][0]["doc_id"]
        return reply(tool_use("submit_report", diagnosis_citing(service, kind="document", ref=found)))

    result, _ = run(env, reply(tool_use("search_runbooks", {"query": env.alert.title, "k": 3})), cite_first_hit)

    assert result.ok and result.report.root_cause.citations[0].kind == "document"


def test_a_failed_search_produces_no_evidence_to_cite(agent_env):
    env = agent_env()
    service = env.scenario.root_cause_service
    cited = diagnosis_citing(service)  # cites the catalog entry; the lookup below will FAIL

    result, _ = run(
        env,
        reply(tool_use("get_service", {"name": "no-such-service"})),
        reply(tool_use("submit_report", cited)),
        config=AgentConfig(max_iterations=2),
    )

    assert not result.ok and result.trace.failure_reason == "invalid_report"


def test_the_insufficient_evidence_path_needs_no_investigation_at_all(agent_env):
    result, _ = run(agent_env(), reply(submit()))

    assert result.ok and result.report.outcome == "insufficient_evidence" and result.report.root_cause is None


# ------------------------------------------------- stopping without submitting


def test_a_model_that_stops_talking_is_nudged_once_then_fails(agent_env):
    env = agent_env()

    nudged, client = run(env, reply(text("Looks like a database problem.")), reply(submit()))
    assert nudged.ok
    assert client.requests[1]["messages"][-1] == {"role": "user", "content": NUDGE}
    assert nudged.trace.turns[0].notes == ["nudged_to_submit"]

    gave_up, _ = run(env, reply(text("hmm")), reply(text("still thinking")))
    assert (gave_up.trace.status, gave_up.trace.failure_reason) == ("failed", "no_report")
    assert gave_up.report is None and len(gave_up.trace.turns) == 2


def test_an_empty_response_is_not_echoed_back_as_an_empty_assistant_turn(agent_env):
    _, client = run(agent_env(), reply(), reply(submit()))

    assert client.requests[1]["messages"][1]["content"] == [{"type": "text", "text": PLACEHOLDER_TEXT}]


def test_a_truncated_response_runs_none_of_its_tool_calls(agent_env):
    env = agent_env()
    cut_off = reply(text("Let me check"), tool_use("page_oncall", {"team": "x", "severity": "SEV1", "message": "cut"}), stop_reason="max_tokens")

    result, client = run(env, cut_off, reply(submit()))

    assert result.ok and result.trace.tool_calls == 1  # only the submit
    assert env.ctx.pager.records == []
    sent = client.requests[1]["messages"]
    assert all(b["type"] == "text" for b in sent[1]["content"]) and sent[2]["content"] == TRUNCATED
    assert result.trace.turns[0].notes == ["truncated_output"]


def test_an_unexpected_stop_reason_fails_cleanly(agent_env):
    result, _ = run(agent_env(), reply(text("I can't help with that."), stop_reason="refusal"))

    assert (result.trace.status, result.trace.failure_reason) == ("failed", "unexpected_stop")
    assert result.trace.turns[0].stop_reason == "refusal"


def test_a_failing_model_call_fails_the_run_but_keeps_the_trace(agent_env):
    env = agent_env()

    def explode(_request):
        raise ConnectionError("upstream unavailable")

    result, _ = run(env, reply(tool_use("get_service", {"name": "checkout-api"})), explode)

    assert (result.trace.status, result.trace.failure_reason) == ("failed", "api_error")
    assert result.trace.turns[1].error == "ConnectionError: upstream unavailable"
    assert result.trace.turns[0].tool_calls[0].name == "get_service"  # what happened before survives


# --------------------------------------------------------------- side effects


def test_page_oncall_actually_runs_once_per_call_and_is_simulated(agent_env):
    env = agent_env()
    page = {"team": "data-platform", "severity": "SEV2", "message": "Synthetic page: pool exhaustion on the primary."}

    result, _ = run(env, reply(tool_use("page_oncall", page)), reply(submit()))

    assert not result.trace.calls("page_oncall")[0].is_error
    assert len(env.ctx.pager.records) == 1


# ---------------------------------------------------------------------- trace


def test_the_trace_records_every_turn_tool_call_token_and_timing(agent_env):
    env = agent_env()
    service = env.scenario.root_cause_service
    result, _ = run(
        env,
        reply(text("Looking."), tool_use("get_service", {"name": service}), tool_use("get_service", {}), input_tokens=500, output_tokens=40),
        reply(tool_use("submit_report", diagnosis_citing(service)), input_tokens=900, output_tokens=300),
    )
    trace = result.trace

    assert (trace.input_tokens, trace.output_tokens, trace.model_calls) == (1400, 340, 2)
    assert (trace.tool_calls, trace.tool_errors) == (3, 1)  # two lookups and the submit
    first = trace.turns[0]
    assert first.text == "Looking." and first.stop_reason == "tool_use" and first.agent == "single-agent"
    assert (first.input_tokens, first.output_tokens) == (500, 40)
    ok, bad = first.tool_calls
    assert (ok.name, ok.arguments, ok.is_error) == ("get_service", {"name": service}, False)
    assert json.loads(ok.result)["name"] == service
    assert bad.is_error and bad.error_kind == "tool_error" and "missing required" in bad.result
    # with a clock that ticks 10ms per reading, every interval is exactly one tick
    assert first.duration_ms == 10.0 and ok.duration_ms == 10.0 and bad.duration_ms == 10.0
    assert trace.duration_ms > sum(t.duration_ms for t in trace.turns)  # the run includes the loop's own time


def test_the_trace_identifies_the_run_and_what_the_model_was_given(agent_env):
    env = agent_env()
    result, _ = run(env, reply(submit()), agent_name="agent-under-test")
    trace = result.trace

    assert (trace.agent, trace.incident_id, trace.model) == ("agent-under-test", env.incident_id, "scripted")
    assert trace.system_prompt_sha == system_prompt_sha(SYSTEM_PROMPT) and len(trace.system_prompt_sha) == 12
    assert trace.tool_names == [*TOOL_ORDER, "submit_report"]
    assert trace.task == incident_task(env.alert, env.scenario.now)
    assert trace.turns[0].agent == "agent-under-test"
    assert trace.started_at.tzinfo is not None


def test_a_changed_prompt_changes_the_recorded_hash(agent_env):
    one, _ = run(agent_env(), reply(submit()), system_prompt="prompt A")
    two, _ = run(agent_env(), reply(submit()), system_prompt="prompt B")

    assert one.trace.system_prompt_sha != two.trace.system_prompt_sha


def test_the_trace_round_trips_through_json(agent_env):
    env = agent_env()
    result, _ = run(env, reply(tool_use("get_service", {"name": "checkout-api"}), tool_use("get_service", "bad")), reply(submit()))

    restored = RunTrace.model_validate_json(result.trace.model_dump_json())

    assert restored == result.trace
    payload = json.loads(result.trace.model_dump_json())
    assert payload["schema_version"] == 1 and payload["tool_calls"] == 3 and payload["input_tokens"] == 200


def test_a_failed_run_still_has_a_complete_trace(agent_env):
    result, _ = run(agent_env(), reply(tool_use("get_service", {"name": "checkout-api"})), config=AgentConfig(max_iterations=1))

    trace = result.trace
    assert (trace.status, trace.failure_reason) == ("failed", "max_iterations")
    assert trace.duration_ms > 0 and trace.tool_calls == 1 and trace.turns[0].forced_tool == "submit_report"


# ------------------------------------------------- many real incidents, no model


SAMPLE = 12


def test_scripted_investigations_across_many_incidents_never_see_their_own_alert(s_scenarios, agent_env):
    incident_ids = sorted(s_scenarios)[:: max(1, len(s_scenarios) // SAMPLE)][:SAMPLE]
    assert len(incident_ids) >= 10

    for incident_id in incident_ids:
        env = agent_env(incident_id)
        result, _ = run(
            env,
            reply(
                tool_use("search_runbooks", {"query": env.alert.title + " " + env.alert.body[:200], "k": 5}),
                tool_use("search_postmortems", {"query": env.alert.title, "k": 5}),
                tool_use("find_similar_incidents", {"description": env.alert.body[:200], "k": 5}),
                tool_use("query_metrics", {"service": env.scenario.root_cause_service, "metric": "error_rate"}),
            ),
            reply(submit()),
        )
        assert result.ok, incident_id
        shown = " ".join(c.result for c in result.trace.calls())
        assert f'"{incident_id}"' not in shown, f"{incident_id} retrieved its own alert"
        assert result.trace.tool_errors == 0, incident_id
