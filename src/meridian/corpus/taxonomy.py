"""Shared vocabulary for corpus generation: failure categories, which
services plausibly suffer which failure, and the three "fragile" services
the spec calls out as the source of ~40% of incidents."""

from __future__ import annotations

from meridian.catalog import ServiceEntry

FRAGILE_SERVICES = {"postgres-primary", "llm-gateway", "notification-service"}

# Services referenced by stale runbooks that no longer exist in the catalog.
DECOMMISSIONED_SERVICES = [
    "checkout-monolith-v1",
    "varnish-cache-cluster",
    "legacy-recommendation-svc-v1",
    "warehouse-mainframe-v1",
    "sms-gateway-v1",
]

CATEGORY_INFO: dict[str, dict[str, str]] = {
    "5xx_errors": {
        "symptom": "an elevated 5xx error rate",
        "cause": "an unhandled exception path was hit under production load that testing never exercised",
    },
    "latency_spike": {
        "symptom": "p99 latency above its SLO target",
        "cause": "a slow query or an undersized resource pool is queueing requests",
    },
    "connection_pool_exhaustion": {
        "symptom": "requests stalling while waiting on a database connection",
        "cause": "the connection pool is undersized for current traffic and connections are maxed out",
    },
    "disk_full": {
        "symptom": "writes being refused or new work no longer being accepted",
        "cause": "the data volume filled up, usually from unshipped WAL or an unvacuumed table",
    },
    "replication_lag": {
        "symptom": "reads returning stale or out-of-date data",
        "cause": "the replica has fallen behind the primary, usually from a long-running query blocking replay",
    },
    "rate_limit_exhaustion": {
        "symptom": "requests queueing or being rejected outright",
        "cause": "aggregate request volume exceeded the provider's quota",
    },
    "quality_degradation": {
        "symptom": "output quality dropping with no traditional error signal",
        "cause": "a routing or model-version change degraded output quality without tripping a health check",
    },
    "third_party_outage": {
        "symptom": "requests to an external provider failing or timing out",
        "cause": "the third-party provider itself is degraded, not anything on our side",
    },
    "race_condition": {
        "symptom": "inconsistent or duplicated state under concurrent load",
        "cause": "two concurrent operations both read stale state before either write committed",
    },
    "schema_mismatch": {
        "symptom": "requests failing validation unexpectedly",
        "cause": "a caller is still sending a previous version of the request schema",
    },
    "misconfiguration": {
        "symptom": "unexpected behavior with no code change involved",
        "cause": "a configuration change had a broader blast radius than intended",
    },
    "cache_eviction": {
        "symptom": "elevated latency and a rise in cold-cache misses",
        "cause": "an eviction policy or memory limit change is evicting entries faster than expected",
    },
    "stale_data": {
        "symptom": "results or dashboards reflecting outdated state with no errors thrown",
        "cause": "a background refresh or index job has been failing silently",
    },
    "certificate_expiry": {
        "symptom": "auth or TLS failures with no code change involved",
        "cause": "a certificate expired without being auto-rotated in time",
    },
    "deploy_regression": {
        "symptom": "a symptom that started immediately after a deploy",
        "cause": "the most recent deploy introduced a regression",
    },
    "job_failure": {
        "symptom": "a batch or background job no longer producing fresh output",
        "cause": "the job has been failing without alerting directly on job failure",
    },
    "memory_leak": {
        "symptom": "gradually increasing memory usage and periodic restarts",
        "cause": "a memory leak accumulates until the process is killed for excess memory use and restarts",
    },
    "upstream_timeout": {
        "symptom": "elevated latency or errors tracing to one specific upstream call",
        "cause": "a synchronous call to a slow or degraded upstream is blocking the request path",
    },
}

# Which categories are plausible for a service, keyed by owning team -- mirrors
# the layer groupings from the catalog itself.
LAYER_POOLS: dict[str, list[str]] = {
    "edge-platform": ["5xx_errors", "latency_spike", "deploy_regression", "misconfiguration"],
    "payments-platform": ["connection_pool_exhaustion", "upstream_timeout", "5xx_errors", "latency_spike"],
    "commerce-platform": ["5xx_errors", "race_condition", "latency_spike", "cache_eviction", "deploy_regression"],
    "identity-platform": ["connection_pool_exhaustion", "cache_eviction", "certificate_expiry", "5xx_errors"],
    "growth-platform": ["third_party_outage", "stale_data", "latency_spike", "quality_degradation"],
    "data-platform": ["disk_full", "replication_lag", "connection_pool_exhaustion", "job_failure", "memory_leak"],
    "ai-platform": ["rate_limit_exhaustion", "quality_degradation", "upstream_timeout", "latency_spike"],
    "fulfilment-platform": ["5xx_errors", "schema_mismatch", "third_party_outage", "latency_spike"],
    "external": ["third_party_outage"],
    "platform-infra": ["job_failure", "misconfiguration", "certificate_expiry", "5xx_errors"],
}


def pool(catalog: dict[str, ServiceEntry], service: str) -> list[str]:
    return LAYER_POOLS[catalog[service].owner]


def services_with_category(catalog: dict[str, ServiceEntry], category: str) -> list[str]:
    return sorted(s for s, e in catalog.items() if category in LAYER_POOLS[e.owner])


# Two same-category, different-mechanism root causes for a single service --
# used for near-duplicate pairs on services with fewer than two dependencies
# (so the "which dependency is to blame" pattern doesn't apply).
MECHANISM_PAIRS: dict[str, dict[str, str]] = {
    "disk_full": {
        "id_a": "wal-bloat",
        "cause_a": "unshipped WAL segments accumulated after a replica fell behind, filling the data volume",
        "fix_a": "ship or rotate the backlogged WAL segments, then investigate why the replica fell behind",
        "id_b": "unvacuumed-table",
        "cause_b": "a large table was never vacuumed and its dead-tuple bloat filled the data volume",
        "fix_b": "run a manual VACUUM on the offending table and check autovacuum settings for that table",
    },
    "memory_leak": {
        "id_a": "connection-leak",
        "cause_a": "connections are being opened but never released, so memory grows until the process restarts",
        "fix_a": "audit the connection lifecycle for a missing close/release path and patch the leak",
        "id_b": "unbounded-cache",
        "cause_b": "an in-process cache has no eviction policy and grows without bound",
        "fix_b": "add a size or TTL bound to the offending cache and redeploy",
    },
    "certificate_expiry": {
        "id_a": "rotation-failure",
        "cause_a": "the automated rotation job silently failed and the old certificate expired before anyone noticed",
        "fix_a": "issue a new certificate manually and fix the rotation job's alerting so this fails loudly next time",
        "id_b": "wrong-validity-window",
        "cause_b": "the certificate was issued with a shorter validity window than the rotation schedule assumed",
        "fix_b": "issue a new certificate and correct the rotation schedule to match the actual validity window",
    },
    "rate_limit_exhaustion": {
        "id_a": "traffic-burst",
        "cause_a": "a sudden burst in legitimate traffic exceeded the configured rate limit",
        "fix_a": "raise the rate limit temporarily and investigate the traffic source before making it permanent",
        "id_b": "quota-downgrade",
        "cause_b": "the upstream provider silently lowered the account's quota tier",
        "fix_b": "check the provider's account dashboard for a quota change and request it be restored",
    },
}
