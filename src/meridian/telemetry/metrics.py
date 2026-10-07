"""Metric definitions, per-service baselines, and how each failure category
shows up (or doesn't) in them.

The shapes here are what make the synthetic world worth reasoning over:
connection-pool exhaustion saturates a pool metric and drags latency up, a
full disk climbs *before* the incident and then errors out, a memory leak
ramps for two hours, and quality degradation / stale data leave every metric
untouched -- because in real life they do, which is the point of those cases.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from meridian.catalog import ServiceEntry
from meridian.telemetry import rng


@dataclass(frozen=True)
class MetricSpec:
    name: str
    unit: str
    description: str
    noise: float  # relative standard deviation of per-minute noise


METRICS: dict[str, MetricSpec] = {
    spec.name: spec
    for spec in (
        MetricSpec("request_rate_rps", "requests/s", "Requests per second the service is handling.", 0.05),
        MetricSpec("error_rate", "ratio 0-1", "Fraction of requests that failed (5xx / timeouts).", 0.25),
        MetricSpec("latency_p99_ms", "ms", "99th-percentile request latency.", 0.06),
        MetricSpec("cpu_percent", "percent", "CPU utilization across the service's instances.", 0.05),
        MetricSpec("memory_percent", "percent", "Memory utilization across the service's instances.", 0.015),
        MetricSpec("disk_used_percent", "percent", "Disk usage of the service's data volume.", 0.003),
        MetricSpec(
            "connection_pool_in_use_percent", "percent", "Share of the database connection pool in use.", 0.06
        ),
        MetricSpec("queue_depth", "messages", "Backlog of unprocessed messages / consumer lag.", 0.30),
    )
}

_UNIVERSAL = ["request_rate_rps", "error_rate", "latency_p99_ms", "cpu_percent", "memory_percent"]
_EXTERNAL = ["request_rate_rps", "error_rate", "latency_p99_ms"]  # observed from Meridian's side only
_PERCENT = {"cpu_percent", "memory_percent", "disk_used_percent", "connection_pool_in_use_percent"}
_DIURNAL_STRENGTH = {"request_rate_rps": 0.30, "cpu_percent": 0.20, "connection_pool_in_use_percent": 0.25}


def available_metrics(catalog: dict[str, ServiceEntry], service: str) -> list[str]:
    entry = catalog[service]
    if entry.tier == "external":
        return list(_EXTERNAL)
    metrics = list(_UNIVERSAL)
    if (entry.owner == "data-platform" and service != "redis-cache") or service == "log-aggregator":
        metrics.append("disk_used_percent")
    if service in {"postgres-primary", "postgres-replica"} or {"postgres-primary", "postgres-replica"} & set(
        entry.depends_on
    ):
        metrics.append("connection_pool_in_use_percent")
    if service == "kafka-broker" or "kafka-broker" in entry.depends_on or service == "warehouse-etl":
        metrics.append("queue_depth")
    return metrics


def baseline(catalog: dict[str, ServiceEntry], service: str, metric: str) -> float:
    """Typical level of `metric` for `service`, before diurnal variation."""
    entry = catalog[service]
    key = ("baseline", service, metric)
    if metric == "request_rate_rps":
        low, high = {1: (800, 2500), 2: (100, 600), 3: (5, 40), "external": (200, 1000)}[entry.tier]
        return rng.uniform(low, high, *key)
    if metric == "error_rate":
        # Healthy services burn a fraction of their budget; derived from the
        # SLO so a 99.95% service doesn't idle at an error rate that would
        # blow its own budget.
        budget = 1.0 - entry.slo.availability / 100.0
        return budget * rng.uniform(0.15, 0.5, *key)
    if metric == "latency_p99_ms":
        target = entry.slo.latency_p99_ms or 400
        return target * rng.uniform(0.35, 0.55, *key)
    if metric == "cpu_percent":
        return rng.uniform(20, 45, *key)
    if metric == "memory_percent":
        return rng.uniform(40, 60, *key)
    if metric == "disk_used_percent":
        return rng.uniform(30, 55, *key)
    if metric == "connection_pool_in_use_percent":
        return rng.uniform(15, 35, *key)
    if metric == "queue_depth":
        return rng.uniform(5, 50, *key)
    raise KeyError(metric)


def diurnal(metric: str, t: datetime) -> float:
    strength = _DIURNAL_STRENGTH.get(metric, 0.02)
    hour = t.hour + t.minute / 60.0
    return 1.0 + strength * math.sin(2 * math.pi * (hour - 8.0) / 24.0)


def expected(catalog: dict[str, ServiceEntry], service: str, metric: str, t: datetime) -> float:
    """What the metric would read with nothing wrong: the noiseless seasonal
    baseline a monitoring system would plot as the "expected" band."""
    return baseline(catalog, service, metric) * diurnal(metric, t)


def clip(metric: str, value: float) -> float:
    if metric in _PERCENT:
        return min(max(value, 0.0), 100.0)
    if metric == "error_rate":
        return min(max(value, 0.0), 1.0)
    return max(value, 0.0)


# ---------------------------------------------------------------- effects


@dataclass(frozen=True)
class Effect:
    """How an incident perturbs one metric, as a function of minutes since the
    incident's onset. `start_min` may be negative: a disk fills for hours
    before the moment it starts refusing writes."""

    metric: str
    kind: str  # "add" (+magnitude), "mult" (x magnitude), "to" (move toward magnitude)
    magnitude: float
    start_min: float = 0.0
    ramp_min: float = 0.0

    def progress(self, minutes_since_onset: float) -> float:
        elapsed = minutes_since_onset - self.start_min
        if elapsed < 0:
            return 0.0
        return 1.0 if self.ramp_min <= 0 else min(1.0, elapsed / self.ramp_min)

    def apply(self, value: float, minutes_since_onset: float, amplitude: float = 1.0) -> float:
        p = self.progress(minutes_since_onset) * amplitude
        if self.kind == "add":
            return value + self.magnitude * p
        if self.kind == "mult":
            return value * (1.0 + (self.magnitude - 1.0) * p)
        if self.kind == "to":
            return value + (self.magnitude - value) * p
        raise ValueError(self.kind)


# Categories with no entry (or an empty list) leave metrics untouched on
# purpose: quality degradation and stale data produce no errors and no
# latency change, so absence of a metric anomaly must never be read as
# absence of a problem.
CATEGORY_EFFECTS: dict[str, list[Effect]] = {
    "5xx_errors": [Effect("error_rate", "add", 0.06, ramp_min=2), Effect("latency_p99_ms", "mult", 1.4, ramp_min=2)],
    "latency_spike": [
        Effect("latency_p99_ms", "mult", 5.0, ramp_min=5),
        Effect("error_rate", "add", 0.004, ramp_min=5),
    ],
    "connection_pool_exhaustion": [
        Effect("connection_pool_in_use_percent", "to", 100.0, ramp_min=20),
        Effect("latency_p99_ms", "mult", 6.0, ramp_min=20),
        Effect("error_rate", "add", 0.04, ramp_min=20),
    ],
    "disk_full": [
        Effect("disk_used_percent", "to", 100.0, start_min=-90, ramp_min=90),
        Effect("error_rate", "add", 0.35, ramp_min=1),
    ],
    "replication_lag": [Effect("latency_p99_ms", "mult", 3.0, ramp_min=15), Effect("error_rate", "add", 0.01, ramp_min=15)],
    "rate_limit_exhaustion": [Effect("error_rate", "add", 0.18, ramp_min=3), Effect("latency_p99_ms", "mult", 1.6, ramp_min=3)],
    "quality_degradation": [],
    "third_party_outage": [Effect("error_rate", "add", 0.30, ramp_min=1), Effect("latency_p99_ms", "mult", 4.0, ramp_min=1)],
    "race_condition": [Effect("error_rate", "add", 0.012, ramp_min=1)],
    "schema_mismatch": [Effect("error_rate", "add", 0.05, ramp_min=1)],
    "misconfiguration": [Effect("error_rate", "add", 0.03, ramp_min=1), Effect("latency_p99_ms", "mult", 1.5, ramp_min=1)],
    "cache_eviction": [Effect("latency_p99_ms", "mult", 2.5, ramp_min=10), Effect("cpu_percent", "mult", 1.6, ramp_min=10)],
    "stale_data": [],
    "certificate_expiry": [Effect("error_rate", "add", 0.95)],
    "deploy_regression": [
        Effect("error_rate", "add", 0.07, ramp_min=2),
        Effect("latency_p99_ms", "mult", 2.2, ramp_min=2),
        Effect("cpu_percent", "mult", 1.4, ramp_min=2),
    ],
    "job_failure": [Effect("queue_depth", "mult", 40.0, ramp_min=30)],  # only visible where a queue metric exists
    "memory_leak": [
        Effect("memory_percent", "to", 99.0, start_min=-120, ramp_min=120),
        Effect("error_rate", "add", 0.02, ramp_min=2),
    ],
    "upstream_timeout": [Effect("latency_p99_ms", "mult", 6.0, ramp_min=3), Effect("error_rate", "add", 0.05, ramp_min=3)],
}

# What a downstream service of the failing one can show: errors and latency only.
PROPAGATING_METRICS = {"error_rate", "latency_p99_ms"}
