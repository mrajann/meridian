"""Session-scoped fixtures shared by the tool-layer tests: the catalog, the
generated corpus, a hashing-embedder index built once, and every incident's
synthetic scenario. (Older test modules define their own module-scoped
fixtures and are unaffected.)"""

import pytest

from meridian.catalog import load_catalog
from meridian.corpus import generate_corpus
from meridian.indexing import HashingEmbedder, VectorIndex, build_index
from meridian.retrieval import Retriever
from meridian.telemetry import build_scenarios
from meridian.tools import build_context


@pytest.fixture(scope="session")
def s_catalog():
    return load_catalog()


@pytest.fixture(scope="session")
def s_documents(s_catalog):
    return generate_corpus(s_catalog)


@pytest.fixture(scope="session")
def s_retriever(tmp_path_factory, s_catalog, s_documents):
    embedder = HashingEmbedder()
    index = VectorIndex(tmp_path_factory.mktemp("tools_chroma"), embedder)
    build_index(s_documents, s_catalog, embedder, index)
    return Retriever(index)


@pytest.fixture(scope="session")
def s_scenarios(s_documents, s_catalog):
    return build_scenarios(s_documents, s_catalog)


@pytest.fixture(scope="session")
def s_ctx(s_catalog, s_retriever):
    """A context with no active incident: a healthy platform at the default 'now'."""
    return build_context(s_catalog, s_retriever)


@pytest.fixture
def ctx_for(s_ctx, s_scenarios):
    """ctx_for(incident_id) -> a fresh context investigating that incident."""

    def make(incident_id: str):
        return s_ctx.with_scenario(s_scenarios[incident_id])

    return make


@pytest.fixture
def find_scenario(s_scenarios):
    """find_scenario(**filters) -> first Scenario whose attributes match, in
    incident-id order so the pick is stable."""

    def find(predicate=None, **attrs):
        for incident_id in sorted(s_scenarios):
            sc = s_scenarios[incident_id]
            if all(getattr(sc, k) == v for k, v in attrs.items()) and (predicate is None or predicate(sc)):
                return sc
        raise LookupError(f"no scenario matches {attrs}")

    return find


@pytest.fixture(scope="session")
def valid_args():
    """valid_args(scenario) -> {tool name: arguments for one plausible, valid
    call}. Every registered tool must have an entry: tests that sweep the
    registry fail loudly for a tool that doesn't, so a new tool cannot slip
    past them by omission."""

    def build(scenario):
        """One plausible, valid call per tool for the given incident."""
        root = scenario.root_cause_service if scenario else "checkout-api"
        return {
            "search_runbooks": {"query": "elevated error rate and latency", "k": 3},
            "search_postmortems": {"query": "services erroring at once", "k": 3},
            "find_similar_incidents": {"description": "error rate elevated on several services", "k": 3},
            "get_service": {"name": root},
            "get_dependencies": {"name": root, "depth": 2},
            "get_dependents": {"name": root, "depth": 2},
            "query_metrics": {"service": root, "metric": "error_rate", "window": "1h"},
            "get_deploy_history": {"service": root, "window": "24h"},
            "compute_error_budget": {"service": root},
            "get_oncall": {"team": "data-oncall"},
            "page_oncall": {"team": "data-oncall", "severity": "SEV2", "message": "synthetic test page for the registry tests"},
        }

    return build


# ------------------------------------------------------------ agent fixtures


@pytest.fixture
def agent_env(s_catalog, s_documents, s_scenarios, ctx_for):
    """agent_env(incident_id=None) -> an investigation ready to run: the
    alert, its scenario, a context with its own telemetry and pager, and a
    Toolset. Defaults to a cascade incident (the interesting case)."""
    from types import SimpleNamespace

    from meridian.tools import Toolset

    def make(incident_id: str | None = None):
        incident_id = incident_id or sorted(i for i in s_scenarios if i.startswith("alert-cascade-"))[0]
        ctx = ctx_for(incident_id)
        alert = next(d for d in s_documents if d.doc_id == incident_id)
        return SimpleNamespace(
            incident_id=incident_id,
            alert=alert,
            scenario=s_scenarios[incident_id],
            ctx=ctx,
            toolset=Toolset(ctx),
            catalog=s_catalog,
        )

    return make


# ------------------------------------------------------ multi-agent fixtures


@pytest.fixture
def ma(agent_env, valid_args):
    """Helpers for driving the four-agent pipeline with scripted models.

    ma.client(env, **overrides) -> a RoutedClient where each agent follows a
    default, valid script unless overridden with a list of steps (responses or
    callables taking the request). ma.clients[agent] are the per-agent
    ScriptedClients, whose .requests show exactly what each agent was sent.
    """
    import json
    from types import SimpleNamespace

    from meridian.agent.scripted import RoutedClient, ScriptedClient, reply, tool_use
    from meridian.multiagent import prompts

    def last_result(request, index=0):
        return json.loads(request["messages"][-1]["content"][index]["content"])

    def triage_report(env, **overrides):
        root = env.scenario.root_cause_service
        report = {
            "severity": "SEV2",
            "severity_rationale": "A tier-1 service is partly degraded for customers.",
            "cascade": False,
            "affected_services": [root],
            "investigation_targets": [root],
            "blast_radius": "The root service and the services that depend on it are degraded.",
            "customer_impact": "Some customers see errors when browsing or buying.",
            "evidence": [{"kind": "catalog", "ref": root, "supports": "the service was looked up in the catalog"}],
        }
        return {**report, **overrides}

    def investigation_report(**overrides):
        report = {
            "outcome": "insufficient_evidence",
            "evidence_gaps": ["No document describes this failure mode and telemetry is ambiguous."],
            "recommended_action": "Ask the owning team to inspect the upstream service directly.",
        }
        return {**report, **overrides}

    def escalation_report(team, **overrides):
        report = {
            "action": "notify_business_hours",
            "team": team,
            "reasoning": "Severity two, error budget healthy, no need to wake anyone.",
            "budget_assessment": "Budget remaining is healthy.",
        }
        return {**report, **overrides}

    def update_report(**overrides):
        report = {
            "headline": "Some customers are seeing errors",
            "customer_impact": "Some customers may see errors while browsing or buying right now.",
            "status": "investigating",
            "confirmed": ["Some customers are seeing errors at the moment."],
            "what_we_are_doing": "Our engineers are working to find the cause right now.",
            "next_update_minutes": 30,
        }
        return {**report, **overrides}

    def default_steps(env):
        root = env.scenario.root_cause_service
        return {
            "triage": [
                reply(tool_use("get_service", {"name": root})),
                reply(tool_use("submit_triage", triage_report(env))),
            ],
            "investigator": [reply(tool_use("submit_investigation", investigation_report()))],
            "escalation": [
                reply(tool_use("get_service", {"name": root})),
                lambda r: reply(tool_use("get_oncall", {"team": last_result(r)["owner"]})),
                lambda r: reply(tool_use("submit_escalation", escalation_report(last_result(r)["team"]))),
            ],
            "comms": [reply(tool_use("submit_update", update_report()))],
        }

    prompt_of = {
        "triage": prompts.TRIAGE_PROMPT,
        "investigator": prompts.INVESTIGATOR_PROMPT,
        "escalation": prompts.ESCALATION_PROMPT,
        "comms": prompts.COMMS_PROMPT,
    }

    def client(env, **overrides):
        steps = {**default_steps(env), **overrides}
        clients = {name: ScriptedClient(*steps[name]) for name in prompt_of}
        routed = RoutedClient({prompt_of[name]: clients[name] for name in prompt_of})
        routed.clients = clients
        return routed

    return SimpleNamespace(
        client=client,
        default_steps=default_steps,
        last_result=last_result,
        triage_report=triage_report,
        investigation_report=investigation_report,
        escalation_report=escalation_report,
        update_report=update_report,
        prompt_of=prompt_of,
        valid_args=valid_args,
    )
