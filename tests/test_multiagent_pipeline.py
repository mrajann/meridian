import json

import pytest

from meridian.agent import RunTrace
from meridian.agent.scripted import ScriptedClient, reply, text, tool_use
from meridian.agent.trace import HandoffTrace, PipelineTrace
from meridian.multiagent import (
    AGENT_TOOLS,
    CustomerUpdate,
    EscalationDecision,
    IncidentPacket,
    Investigation,
    MultiAgentPipeline,
    TriageHandoff,
)
from meridian.multiagent import prompts
from meridian.tools import TOOL_ORDER

AGENTS = ["triage", "investigator", "escalation", "comms"]


def run_pipeline(env, ma, **overrides):
    client = ma.client(env, **overrides)
    pipeline = MultiAgentPipeline(client, env.ctx, env.catalog)
    return pipeline.run(env.alert, env.scenario.now), client


def first_message(client, agent):
    return client.clients[agent].requests[0]["messages"][0]["content"]


def handoff(trace, frm, to):
    [match] = [h for h in trace.handoffs if (h.from_agent, h.to_agent) == (frm, to)]
    return match


# ------------------------------------------------------------- the happy path


def test_four_agents_run_in_order_and_produce_a_complete_packet(agent_env, ma):
    env = agent_env()
    run, _ = run_pipeline(env, ma)

    assert run.ok and run.trace.status == "completed" and run.trace.failures == []
    assert run.trace.path == AGENTS
    assert [a.agent for a in run.trace.agents] == AGENTS
    packet = run.packet
    assert isinstance(packet, IncidentPacket) and packet.status == "completed"
    assert isinstance(packet.triage, TriageHandoff) and isinstance(packet.investigation, Investigation)
    assert isinstance(packet.escalation, EscalationDecision) and isinstance(packet.customer_update, CustomerUpdate)
    assert packet.incident_id == env.incident_id and packet.investigation_source == "agent"


def test_the_graph_is_a_langgraph_graph_with_the_four_agents_as_nodes(agent_env, ma):
    env = agent_env()
    pipeline = MultiAgentPipeline(ma.client(env), env.ctx, env.catalog)

    nodes = set(pipeline.graph.get_graph().nodes)

    assert set(AGENTS) <= nodes and type(pipeline.graph).__module__.startswith("langgraph")


# ------------------------------------------------------------------ toolsets


def test_each_agent_has_exactly_the_tools_the_spec_gives_it(agent_env, ma):
    env = agent_env()
    run, client = run_pipeline(env, ma)

    expected = {
        "triage": ["get_service", "get_dependencies", "get_dependents", "query_metrics", "submit_triage"],
        "investigator": [
            "search_runbooks", "search_postmortems", "find_similar_incidents", "get_deploy_history",
            "query_metrics", "submit_investigation",
        ],
        "escalation": ["get_oncall", "compute_error_budget", "get_service", "page_oncall", "submit_escalation"],
        "comms": ["submit_update"],
    }
    for agent, tools in expected.items():
        offered = [t["name"] for t in client.clients[agent].requests[0]["tools"]]
        assert sorted(offered) == sorted(tools), agent
        assert sorted(run.trace.agent(agent).tool_names) == sorted(tools), agent


def test_comms_has_no_tools_at_all_besides_its_output(agent_env, ma):
    env = agent_env()
    run, client = run_pipeline(env, ma)

    assert AGENT_TOOLS["comms"] == ()
    assert [t["name"] for t in client.clients["comms"].requests[0]["tools"]] == ["submit_update"]
    assert run.trace.agent("comms").tool_calls == 1  # the submission, nothing else


def test_every_tool_belongs_to_at_least_one_agent_and_the_shared_ones_are_deliberate():
    used = [t for tools in AGENT_TOOLS.values() for t in tools]

    assert set(used) == set(TOOL_ORDER)
    assert sorted(t for t in set(used) if used.count(t) > 1) == ["get_service", "query_metrics"]


FORBIDDEN = [(agent, tool) for agent in AGENT_TOOLS for tool in TOOL_ORDER if tool not in AGENT_TOOLS[agent]]


def test_the_forbidden_pairs_cover_every_agent_and_tool():
    # 4 agents x 11 tools = 44 pairs; the spec allows 4 + 5 + 4 + 0 = 13 of them
    assert len(FORBIDDEN) == 31
    assert {agent for agent, _ in FORBIDDEN} == set(AGENTS)
    assert {tool for _, tool in FORBIDDEN} == set(TOOL_ORDER)  # every tool is off-limits to someone


@pytest.mark.parametrize("agent, tool", FORBIDDEN)
def test_an_agent_cannot_call_a_tool_outside_its_toolset(agent_env, ma, agent, tool):
    env = agent_env()
    attempt = reply(tool_use(tool, ma.valid_args(env.scenario)[tool], id="toolu_forbidden"))
    steps = ma.default_steps(env)

    run, client = run_pipeline(env, ma, **{agent: [attempt, *steps[agent]]})

    [call] = [c for c in run.trace.agent(agent).calls(tool)]
    assert call.is_error and call.error_kind == "tool_error" and "unknown tool" in call.result
    assert env.ctx.pager.records == []  # in particular, nobody was paged
    assert run.trace.status == "completed"  # the agent recovered and finished


# ------------------------------------------------------------------ handoffs


def test_every_data_flow_is_a_recorded_validated_handoff(agent_env, ma):
    run, _ = run_pipeline(agent_env(), ma)

    flows = [(h.from_agent, h.to_agent, h.schema_name) for h in run.trace.handoffs]
    assert flows == [
        ("triage", "investigator", "TriageHandoff"),
        ("triage", "escalation", "TriageHandoff"),
        ("triage", "comms", "TriageHandoff"),
        ("investigator", "escalation", "Investigation"),
        ("investigator", "comms", "Investigation"),
        ("escalation", "comms", "EscalationDecision"),
        ("comms", "output", "CustomerUpdate"),
    ]
    assert all(h.valid and h.source == "agent" and h.error is None for h in run.trace.handoffs)


def test_the_recorded_payload_is_exactly_what_the_next_agent_is_shown(agent_env, ma):
    env = agent_env()
    run, client = run_pipeline(env, ma)

    shown = {
        ("triage", "investigator"): first_message(client, "investigator"),
        ("triage", "escalation"): first_message(client, "escalation"),
        ("investigator", "escalation"): first_message(client, "escalation"),
        ("triage", "comms"): first_message(client, "comms"),
        ("investigator", "comms"): first_message(client, "comms"),
        ("escalation", "comms"): first_message(client, "comms"),
    }
    for (frm, to), message in shown.items():
        payload = handoff(run.trace, frm, to).payload
        assert json.dumps(payload, indent=2) in message, (frm, to)


def test_handoff_payloads_round_trip_to_the_packet(agent_env, ma):
    run, _ = run_pipeline(agent_env(), ma)

    assert TriageHandoff.model_validate(handoff(run.trace, "triage", "investigator").payload) == run.packet.triage
    assert Investigation.model_validate(handoff(run.trace, "investigator", "comms").payload) == run.packet.investigation
    assert EscalationDecision.model_validate(handoff(run.trace, "escalation", "comms").payload) == run.packet.escalation
    assert CustomerUpdate.model_validate(handoff(run.trace, "comms", "output").payload) == run.packet.customer_update


def test_the_investigator_is_told_where_triage_says_the_root_cause_is(agent_env, ma):
    env = agent_env()
    upstream = "postgres-primary"
    alerting = env.scenario.root_cause_service
    triage = ma.triage_report(env, cascade=True, affected_services=[alerting, "checkout-api"] if alerting != "checkout-api" else ["checkout-api", "cart-service"], investigation_targets=[upstream])
    steps = ma.default_steps(env)
    steps["triage"] = [reply(tool_use("get_service", {"name": alerting})), reply(tool_use("submit_triage", triage))]

    run, client = run_pipeline(env, ma, triage=steps["triage"])

    message = first_message(client, "investigator")
    assert '"investigation_targets": [\n    "postgres-primary"\n  ]' in message
    assert '"cascade": true' in message
    assert message.index("Triage handoff") < message.index("Investigate the root cause.")


def test_comms_sees_only_what_the_other_agents_found(agent_env, ma):
    env = agent_env()
    _, client = run_pipeline(env, ma)

    message = first_message(client, "comms")

    assert env.alert.body.strip() not in message and env.alert.title not in message
    assert env.incident_id not in message
    assert all(name in message for name in ("Triage handoff", "Investigation handoff", "Escalation decision"))


def test_the_investigator_gets_the_alert_and_the_handoff_but_not_the_paging_decision(agent_env, ma):
    env = agent_env()
    _, client = run_pipeline(env, ma)

    message = first_message(client, "investigator")

    assert env.alert.title in message and "Escalation" not in message


def test_ground_truth_never_reaches_any_agent(agent_env, ma):
    env = agent_env()
    _, client = run_pipeline(env, ma)

    for agent in AGENTS:
        sent = json.dumps(client.clients[agent].requests[0])
        for key in ("correct_runbook", "has_matching_runbook", "adversarial_case", "root_cause_category"):
            assert key not in sent, (agent, key)


def test_prompts_name_no_service_or_document_and_stay_in_their_lane(s_catalog, s_documents):
    for name in ("TRIAGE_PROMPT", "INVESTIGATOR_PROMPT", "ESCALATION_PROMPT", "COMMS_PROMPT"):
        prompt = getattr(prompts, name).lower()
        assert [s for s in s_catalog if s in prompt] == [], name
        assert [d.doc_id for d in s_documents if d.doc_id.lower() in prompt] == [], name
    triage, investigator, escalation, comms = (getattr(prompts, n) for n in ("TRIAGE_PROMPT", "INVESTIGATOR_PROMPT", "ESCALATION_PROMPT", "COMMS_PROMPT"))
    assert "search_runbooks" not in triage and "page_oncall" not in triage
    assert "page_oncall" not in investigator and "compute_error_budget" not in investigator
    assert "search_runbooks" not in escalation and "query_metrics" not in escalation
    assert not any(t in comms for t in TOOL_ORDER)


# ------------------------------------------------------- the agents' own checks


def test_an_agent_that_submits_an_ungrounded_handoff_is_sent_back_to_fix_it(agent_env, ma):
    env = agent_env()
    root = env.scenario.root_cause_service
    fabricated = ma.triage_report(env, evidence=[{"kind": "metric", "ref": f"{root}/error_rate", "supports": "the error rate was elevated"}])
    steps = ma.default_steps(env)["triage"]  # looks up the catalog entry but never queries metrics

    run, client = run_pipeline(env, ma, triage=[steps[0], reply(tool_use("submit_triage", fabricated)), steps[1]])

    submits = run.trace.agent("triage").calls("submit_triage")
    assert [c.is_error for c in submits] == [True, False] and "was not returned by any tool call" in submits[0].result
    assert run.ok


def test_comms_is_rejected_for_leaking_internal_names_and_fixes_it(agent_env, ma):
    env = agent_env()
    leaky = ma.update_report(headline=f"Trouble with {env.scenario.root_cause_service} today")

    run, _ = run_pipeline(env, ma, comms=[reply(tool_use("submit_update", leaky)), reply(tool_use("submit_update", ma.update_report()))])

    submits = run.trace.agent("comms").calls("submit_update")
    assert [c.is_error for c in submits] == [True, False] and "internal terms" in submits[0].result
    assert env.scenario.root_cause_service not in run.packet.customer_update.headline


# ----------------------------------------------------------------- paging


def paging_steps(ma, env, severity_note="Severity two, budget exhausted."):
    root = env.scenario.root_cause_service
    page = {"team": "", "severity": "SEV2", "message": "Synthetic page: upstream failure with customer impact."}
    return [
        reply(tool_use("get_service", {"name": root})),
        lambda r: reply(tool_use("get_oncall", {"team": ma.last_result(r)["owner"]})),
        lambda r: reply(tool_use("page_oncall", {**page, "team": ma.last_result(r)["team"]})),
        lambda r: reply(
            tool_use(
                "submit_escalation",
                ma.escalation_report(
                    ma.last_result(r)["team"], action="page_now", page_id=ma.last_result(r)["page_id"], reasoning=severity_note + " Paging now."
                ),
            )
        ),
    ]


def test_a_page_is_recorded_once_and_the_decision_matches_it(agent_env, ma):
    env = agent_env()

    run, _ = run_pipeline(env, ma, escalation=paging_steps(ma, env))

    [record] = env.ctx.pager.records
    assert run.packet.escalation.action == "page_now" and run.packet.escalation.page_id == record.page_id
    assert run.packet.escalation.team == record.team


def page_made(request):
    """The page_oncall result somewhere in the conversation so far."""
    for message in request["messages"]:
        if message["role"] == "user" and isinstance(message["content"], list):
            for block in message["content"]:
                if block["type"] == "tool_result" and '"page_id"' in block["content"]:
                    return json.loads(block["content"])
    raise AssertionError("no page in the conversation")


def test_an_agent_that_pages_but_reports_no_action_is_made_to_correct_itself(agent_env, ma):
    env = agent_env()
    lie = reply(tool_use("submit_escalation", ma.escalation_report(None, action="no_action")))
    truth = lambda r: reply(
        tool_use("submit_escalation", ma.escalation_report(page_made(r)["team"], action="page_now", page_id=page_made(r)["page_id"]))
    )

    run, _ = run_pipeline(env, ma, escalation=[*paging_steps(ma, env)[:3], lie, truth])

    submits = run.trace.agent("escalation").calls("submit_escalation")
    assert [c.is_error for c in submits] == [True, False] and "you paged" in submits[0].result
    assert len(env.ctx.pager.records) == 1 and run.packet.escalation.action == "page_now"


# ---------------------------------------------------------- failure policy


def failing(_request):
    raise ConnectionError("model unavailable")


def test_if_triage_fails_the_run_ends_and_no_other_agent_is_called(agent_env, ma):
    env = agent_env()
    run, client = run_pipeline(env, ma, triage=[failing])

    assert not run.ok and run.packet is None
    assert run.trace.status == "failed" and run.trace.path == ["triage"]
    assert run.trace.failures == ["triage: api_error"]
    assert [a.agent for a in run.trace.agents] == ["triage"] and run.trace.handoffs == []
    for agent in ("investigator", "escalation", "comms"):
        assert client.clients[agent].requests == []


def test_if_the_investigator_fails_an_honest_unknown_goes_on_so_escalation_still_runs(agent_env, ma):
    env = agent_env()
    run, client = run_pipeline(env, ma, investigator=[failing])

    assert run.trace.status == "partial" and run.trace.failures == ["investigator: api_error"]
    assert run.trace.path == AGENTS  # escalation and comms still ran
    assert run.packet.investigation_source == "system_fallback"
    assert run.packet.investigation.outcome == "insufficient_evidence" and run.packet.investigation.root_cause is None
    assert "api_error" in run.packet.investigation.evidence_gaps[0]
    to_escalation = handoff(run.trace, "investigator", "escalation")
    assert to_escalation.source == "system_fallback" and to_escalation.valid
    assert json.dumps(to_escalation.payload, indent=2) in first_message(client, "escalation")
    assert run.packet.escalation is not None and run.packet.customer_update.status == "investigating"


def test_a_fallback_investigation_can_never_support_a_claimed_cause_in_the_update(agent_env, ma):
    env = agent_env()
    overclaims = [reply(tool_use("submit_update", ma.update_report(status="identified"))), reply(tool_use("submit_update", ma.update_report()))]

    run, _ = run_pipeline(env, ma, investigator=[failing], comms=overclaims)

    assert run.trace.agent("comms").calls("submit_update")[0].is_error
    assert run.packet.customer_update.status == "investigating"


def test_if_escalation_fails_comms_still_writes_and_is_told_there_is_no_decision(agent_env, ma):
    env = agent_env()
    run, client = run_pipeline(env, ma, escalation=[failing])

    assert run.trace.status == "partial" and run.trace.failures == ["escalation: api_error"]
    assert run.packet.escalation is None and run.packet.customer_update is not None
    assert "Unavailable" in first_message(client, "comms")
    assert not any(h.from_agent == "escalation" for h in run.trace.handoffs)


def test_if_comms_fails_the_rest_of_the_packet_survives(agent_env, ma):
    env = agent_env()
    run, _ = run_pipeline(env, ma, comms=[failing])

    assert run.trace.status == "partial" and run.packet.customer_update is None
    assert run.packet.triage and run.packet.investigation and run.packet.escalation
    assert run.trace.failures == ["comms: api_error"]


def test_a_model_that_never_submits_fails_only_its_own_agent(agent_env, ma):
    env = agent_env()
    run, _ = run_pipeline(env, ma, investigator=[reply(text("I think it is the database.")), reply(text("really"))])

    assert run.trace.failures == ["investigator: no_report"] and run.packet.investigation_source == "system_fallback"


# -------------------------------------------------------------------- trace


def test_the_pipeline_trace_says_which_agent_ran_which_tools_and_what_was_passed_on(agent_env, ma):
    env = agent_env()
    root = env.scenario.root_cause_service
    run, _ = run_pipeline(env, ma)
    trace = run.trace

    assert isinstance(trace, PipelineTrace) and trace.architecture == "multi-agent"
    assert [(a.agent, [c.name for c in a.calls()]) for a in trace.agents] == [
        ("triage", ["get_service", "submit_triage"]),
        ("investigator", ["submit_investigation"]),
        ("escalation", ["get_service", "get_oncall", "submit_escalation"]),
        ("comms", ["submit_update"]),
    ]
    assert trace.agents[0].calls("get_service")[0].arguments == {"name": root}
    for agent_trace in trace.agents:
        assert isinstance(agent_trace, RunTrace)
        assert {t.agent for t in agent_trace.turns} == {agent_trace.agent}
        assert agent_trace.incident_id == env.incident_id
    assert all(isinstance(h, HandoffTrace) for h in trace.handoffs)


def test_pipeline_totals_are_the_sum_of_the_agents_and_match_a_single_agent_trace_fields(agent_env, ma):
    run, _ = run_pipeline(agent_env(), ma)
    trace = run.trace

    assert trace.input_tokens == sum(a.input_tokens for a in trace.agents) > 0
    assert trace.output_tokens == sum(a.output_tokens for a in trace.agents) > 0
    assert trace.model_calls == sum(len(a.turns) for a in trace.agents) == 7
    assert trace.tool_calls == sum(a.tool_calls for a in trace.agents) == 7
    assert trace.tool_errors == 0 and len(trace.calls("get_service")) == 2
    single_fields = set(RunTrace.model_computed_fields) | {"duration_ms", "status"}
    assert {"input_tokens", "output_tokens", "model_calls", "tool_calls", "tool_errors", "duration_ms", "status"} <= single_fields
    assert {"input_tokens", "output_tokens", "model_calls", "tool_calls", "tool_errors"} <= set(PipelineTrace.model_computed_fields)


def test_the_pipeline_trace_round_trips_through_json(agent_env, ma):
    run, _ = run_pipeline(agent_env(), ma)

    restored = PipelineTrace.model_validate_json(run.trace.model_dump_json())

    assert restored == run.trace
    payload = json.loads(run.trace.model_dump_json())
    assert payload["schema_version"] == 1 and payload["model_calls"] == 7 and len(payload["handoffs"]) == 7


def test_the_run_is_timed_and_identified(agent_env, ma):
    env = agent_env()
    run, _ = run_pipeline(env, ma)

    assert run.trace.duration_ms > 0 and run.trace.incident_id == env.incident_id
    assert len(run.trace.run_id) == 12 and run.trace.started_at.tzinfo is not None
    assert run.trace.model == "scripted"


def test_each_agent_runs_with_its_own_prompt_hash(agent_env, ma):
    run, _ = run_pipeline(agent_env(), ma)

    shas = [a.system_prompt_sha for a in run.trace.agents]

    assert len(set(shas)) == 4


# ----------------------------------------------- the loop's limits, per agent


def test_an_agent_out_of_turns_is_forced_to_submit_its_own_output_not_the_single_agents(agent_env, ma):
    env = agent_env()
    client = ma.client(env, investigator=[
        reply(tool_use("query_metrics", {"service": env.scenario.root_cause_service, "metric": "error_rate"})),
        reply(tool_use("submit_investigation", ma.investigation_report())),
    ])
    pipeline = MultiAgentPipeline(client, env.ctx, env.catalog, iterations={"investigator": 2})

    run = pipeline.run(env.alert, env.scenario.now)

    first, last = client.clients["investigator"].requests
    assert first["tool_choice"] is None
    assert last["tool_choice"] == {"type": "tool", "name": "submit_investigation"}
    final_message = json.dumps(last["messages"][-1]["content"])
    assert "submit_investigation" in final_message and "submit_report" not in final_message
    assert run.trace.agent("investigator").turns[1].forced_tool == "submit_investigation"
    assert run.trace.status == "completed"


def test_an_agent_that_stops_without_submitting_is_nudged_to_its_own_submit_tool(agent_env, ma):
    env = agent_env()
    client = ma.client(env, comms=[reply(text("Here is an update for customers.")), reply(tool_use("submit_update", ma.update_report()))])

    run = MultiAgentPipeline(client, env.ctx, env.catalog).run(env.alert, env.scenario.now)

    nudge = client.clients["comms"].requests[1]["messages"][-1]["content"]
    assert "submit_update" in nudge and "submit_report" not in nudge and "status=investigating" in nudge
    assert run.trace.status == "completed"


def test_each_agents_iteration_cap_is_independent(agent_env, ma):
    env = agent_env()
    endless = [reply(tool_use("query_metrics", {"service": env.scenario.root_cause_service, "metric": "error_rate"})) for _ in range(5)]
    client = ma.client(env, investigator=endless)

    run = MultiAgentPipeline(client, env.ctx, env.catalog, iterations={"investigator": 3}).run(env.alert, env.scenario.now)

    assert len(client.clients["investigator"].requests) == 3
    assert run.trace.failures == ["investigator: max_iterations"] and run.trace.status == "partial"
    assert len(run.trace.agent("triage").turns) == 2  # the others kept their own budgets


def test_comms_may_claim_a_cause_only_because_the_investigator_found_one(agent_env, ma):
    env = agent_env()
    root = env.scenario.root_cause_service
    cause = {
        "service": root, "category": "other", "confidence": "medium",
        "summary": "The service is degraded and its own metrics show it first.",
        "citations": [{"kind": "metric", "ref": f"{root}/error_rate", "supports": "the error rate deviated on this service"}],
    }
    found = [
        reply(tool_use("query_metrics", {"service": root, "metric": "error_rate"})),
        reply(tool_use("submit_investigation", ma.investigation_report(outcome="root_cause_identified", evidence_gaps=[], root_cause=cause))),
    ]
    claims = [reply(tool_use("submit_update", ma.update_report(
        status="identified", suspected=["We believe a fault in one of our systems is responsible."])))]

    run, _ = run_pipeline(env, ma, investigator=found, comms=claims)

    assert run.packet.investigation.outcome == "root_cause_identified"
    assert run.packet.customer_update.status == "identified" and run.packet.customer_update.suspected
    assert not run.trace.agent("comms").calls("submit_update")[0].is_error  # accepted first time
