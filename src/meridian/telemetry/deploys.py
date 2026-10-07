"""Synthetic deploy records.

Every service has a background cadence of ordinary deploys. On top of that a
scenario can inject (a) a deploy that genuinely caused the incident, and/or
(b) a coincidental one landing just before onset. The two are drawn from
overlapping summary pools and overlapping timing windows on purpose: a deploy
shortly before an incident is evidence, not proof, and the changelog text
should not be a tell.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from meridian.catalog import ServiceEntry
from meridian.telemetry import rng
from meridian.telemetry.scenario import Scenario

_P_DEPLOY_PER_DAY = {1: 0.40, 2: 0.25, 3: 0.10}
_AUTHORS = [
    "a.okafor", "b.lindqvist", "c.moreau", "d.tanaka", "e.haddad", "f.novak",
    "g.santos", "h.petrov", "i.abara", "j.fischer", "k.mehta", "l.duarte",
]

# Bland and risky-sounding summaries are mixed on purpose; both background
# and decoy deploys draw from this whole pool.
_ORDINARY = [
    ("feature", "Update footer copy and legal links"),
    ("dependency", "Bump logging library to latest patch release"),
    ("config", "Rename internal metrics labels"),
    ("feature", "Refactor retry logic in client wrapper"),
    ("dependency", "Upgrade HTTP client library"),
    ("config", "Adjust log sampling rate"),
    ("feature", "Add pagination to list endpoint"),
    ("hotfix", "Fix typo in error message"),
    ("config", "Tune request timeout defaults"),
    ("feature", "Migrate a handler to the shared validation layer"),
]
# Flavored by the failure the deploy really caused; used for only half of
# the causal deploys, the rest read like the ordinary pool above.
_CAUSAL_FLAVORED = {
    "deploy_regression": "Refactor request handling middleware",
    "5xx_errors": "Add stricter input validation to request parser",
    "latency_spike": "Switch lookup to per-item query path",
    "misconfiguration": "Update timeout and rate-limit configuration for downstream calls",
    "schema_mismatch": "Make an optional request field required in the v2 schema",
    "race_condition": "Remove row lock in reservation path as a performance optimization",
    "cache_eviction": "Reduce cache TTL and memory ceiling",
}


@dataclass(frozen=True)
class DeployRecord:
    deploy_id: str
    service: str
    deployed_at: datetime
    version: str
    deployed_by: str
    change_type: str
    change_summary: str
    status: str  # "succeeded" | "rolled_back"


def _record(service: str, when: datetime, change: tuple[str, str], salt: str) -> DeployRecord:
    stamp = when.strftime("%Y%m%d%H%M")
    return DeployRecord(
        deploy_id=f"dep-{service}-{stamp}",
        service=service,
        deployed_at=when,
        version=f"{when.strftime('%Y.%j')}.{int(rng.unit(service, stamp, 'patch') * 20)}",
        deployed_by=rng.choice(_AUTHORS, service, stamp, "author", salt),
        change_type=change[0],
        change_summary=change[1],
        status="rolled_back" if rng.unit(service, stamp, "rollback") < 0.04 else "succeeded",
    )


def _background(catalog: dict[str, ServiceEntry], service: str, start: datetime, end: datetime) -> list[DeployRecord]:
    tier = catalog[service].tier
    if tier == "external":  # a vendor's releases aren't Meridian deploys
        return []
    records = []
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        ordinal = day.toordinal()
        if rng.unit(service, "deploy-day", ordinal) < _P_DEPLOY_PER_DAY[tier]:
            when = day + timedelta(hours=rng.uniform(13, 22, service, "h", ordinal))
            when = when.replace(second=0, microsecond=0)
            change = rng.choice(_ORDINARY, service, "change", ordinal)
            records.append(_record(service, when, change, "bg"))
        day += timedelta(days=1)
    return records


def _injected(scenario: Scenario, service: str) -> list[DeployRecord]:
    if service != scenario.root_cause_service:
        return []
    onset = scenario.onset
    if scenario.deploy_causal:
        when = onset - timedelta(minutes=rng.uniform(2, 22, scenario.seed, "causal-gap"))
        if rng.unit(scenario.seed, "flavored") < 0.5:
            change = ("feature", _CAUSAL_FLAVORED.get(scenario.category, "Refactor request handling middleware"))
        else:
            change = rng.choice(_ORDINARY, scenario.seed, "causal-change")
        return [_record(service, when.replace(second=0, microsecond=0), change, "inj")]
    if scenario.decoy_deploy:
        when = onset - timedelta(minutes=rng.uniform(5, 60, scenario.seed, "decoy-gap"))
        change = rng.choice(_ORDINARY, scenario.seed, "decoy-change")
        return [_record(service, when.replace(second=0, microsecond=0), change, "inj")]
    return []


def deploys_between(
    catalog: dict[str, ServiceEntry],
    scenario: Scenario | None,
    service: str,
    start: datetime,
    end: datetime,
) -> list[DeployRecord]:
    """Deploys of `service` in [start, end], oldest first."""
    records = _background(catalog, service, start, end)
    if scenario is not None:
        records += _injected(scenario, service)
    unique = {r.deploy_id: r for r in records}  # an injected deploy can share a minute with a background one
    return sorted((r for r in unique.values() if start <= r.deployed_at <= end), key=lambda r: r.deployed_at)
