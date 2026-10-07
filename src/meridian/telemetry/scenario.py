"""An incident as the synthetic world sees it: what is really wrong, where,
since when, and whether a deploy actually caused it.

Scenarios are built from a corpus alert's ground-truth labels -- this is the
data generator, so it is the one place that is *supposed* to know the answer.
None of that ground truth (`deploy_causal`, `decoy_deploy`, the category
itself) is ever returned by a tool; tools only expose what the world looks
like (metric series, deploy records), which the agent has to interpret.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from meridian.catalog import ServiceEntry
from meridian.corpus.models import CorpusDocument
from meridian.graph import DependencyGraph
from meridian.telemetry import rng
from meridian.telemetry.metrics import CATEGORY_EFFECTS, PROPAGATING_METRICS, Effect

UTC = timezone.utc
EPOCH = datetime(2026, 1, 5, tzinfo=UTC)  # incidents are spread over the ~10 weeks after this

# Deploys plausibly cause these; everything else (disk full, certificate
# expiry, third-party outages, ...) isn't something a code change does, so a
# deploy near one is coincidence by construction.
ALWAYS_DEPLOY_CAUSED = {"deploy_regression"}
SOMETIMES_DEPLOY_CAUSED = {
    "5xx_errors", "latency_spike", "misconfiguration", "schema_mismatch", "race_condition", "cache_eviction",
}
P_DEPLOY_CAUSED_WHEN_PLAUSIBLE = 0.55
P_COINCIDENTAL_DEPLOY = 0.45  # a non-causal deploy still lands just before onset


@dataclass(frozen=True)
class Blip:
    """A short, unrelated latency bump on some other service -- the kind of
    thing that looks alarming on a chart and means nothing."""

    service: str
    metric: str
    start: datetime
    minutes: float
    multiplier: float


@dataclass(frozen=True)
class Scenario:
    incident_id: str
    onset: datetime  # when the anomaly truly starts
    now: datetime  # when the alert fires; "the present" for every tool call
    root_cause_service: str
    category: str
    symptomatic: dict[str, tuple[float, float]]  # service -> (amplitude 0-1, lag minutes)
    deploy_causal: bool  # ground truth: never exposed by a tool
    decoy_deploy: bool  # ground truth: a non-causal deploy lands just before onset
    blip: Blip | None
    excluded_doc_ids: frozenset[str]  # corpus docs that would give the answer away
    seed: str

    def effects_for(self, service: str) -> list[tuple[Effect, float, float]]:
        """(effect, amplitude, lag in minutes) applying to `service`."""
        effects = CATEGORY_EFFECTS.get(self.category, [])
        if service == self.root_cause_service:
            return [(e, 1.0, 0.0) for e in effects]
        if service in self.symptomatic:
            amplitude, lag = self.symptomatic[service]
            return [(e, amplitude, lag) for e in effects if e.metric in PROPAGATING_METRICS]
        return []


def _base_category(raw: str) -> str:
    return raw.split("__")[0]


def scenario_from_alert(
    alert: CorpusDocument, catalog: dict[str, ServiceEntry], graph: DependencyGraph | None = None
) -> Scenario:
    graph = graph or DependencyGraph(catalog)
    incident_id = alert.doc_id
    meta = alert.metadata
    category = _base_category(meta["root_cause_category"])
    root = meta["root_cause_service"]
    alert_services = [s for s in alert.services if s in catalog]

    # A near-duplicate pair's category carries the blamed dependency as a
    # suffix ("5xx_errors__postgres-primary"): there the fault is really in
    # that dependency and the alerting service is just the one that noticed.
    suffix = meta["root_cause_category"].partition("__")[2]
    if suffix in catalog and suffix in catalog[root].depends_on:
        root = suffix

    symptomatic: dict[str, tuple[float, float]] = {}
    for service in meta.get("affected_services", []):
        if service in catalog and service != root:
            symptomatic[service] = (0.8, rng.uniform(1, 3, incident_id, "lag", service))
    for service in alert_services:  # the service the alert fired on must show it
        if service != root:
            symptomatic[service] = (1.0, rng.uniform(1, 2, incident_id, "lag", service))
    if CATEGORY_EFFECTS.get(category):  # direct dependents feel a weaker ripple
        for service in graph.dependents(root, depth=1):
            symptomatic.setdefault(service, (0.35, rng.uniform(2, 5, incident_id, "lag", service)))

    onset = EPOCH + timedelta(
        days=int(rng.unit(incident_id, "day") * 70),
        hours=int(rng.unit(incident_id, "hour") * 24),
        minutes=int(rng.unit(incident_id, "minute") * 60),
    )
    now = onset + timedelta(minutes=rng.uniform(4, 14, incident_id, "detect"))

    if category in ALWAYS_DEPLOY_CAUSED:
        causal = True
    elif category in SOMETIMES_DEPLOY_CAUSED:
        causal = rng.unit(incident_id, "causal") < P_DEPLOY_CAUSED_WHEN_PLAUSIBLE
    else:
        causal = False
    decoy = (not causal) and rng.unit(incident_id, "decoy") < P_COINCIDENTAL_DEPLOY

    others = sorted(set(catalog) - {root} - set(symptomatic))
    blip_service = rng.choice(others, incident_id, "blip-service")
    blip = Blip(
        service=blip_service,
        metric="latency_p99_ms",
        start=now - timedelta(minutes=rng.uniform(20, 50, incident_id, "blip-start")),
        minutes=3.0,
        multiplier=1.8,
    )

    excluded = {incident_id}
    if incident_id.startswith("alert-cascade-"):  # its postmortem is written after resolution
        excluded.add(incident_id.replace("alert-", "postmortem-", 1))

    return Scenario(
        incident_id=incident_id,
        onset=onset,
        now=now,
        root_cause_service=root,
        category=category,
        symptomatic=symptomatic,
        deploy_causal=causal,
        decoy_deploy=decoy,
        blip=blip,
        excluded_doc_ids=frozenset(excluded),
        seed=incident_id,
    )


def build_scenarios(
    documents: list[CorpusDocument], catalog: dict[str, ServiceEntry]
) -> dict[str, Scenario]:
    graph = DependencyGraph(catalog)
    return {
        doc.doc_id: scenario_from_alert(doc, catalog, graph) for doc in documents if doc.doc_type == "alert"
    }
