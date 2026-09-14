"""Second, larger batch of corpus documents (increment 3 expansion).

The original 32-document batch in generator.py is hand-authored, one document
at a time -- that works at small scale but does not scale to hundreds of
documents. This batch is template-driven instead: a fixed taxonomy of failure
categories, one body template per category, and a deterministic (unweighted-
random-free) assignment of (service, category) pairs to documents. This
mirrors how the spec itself describes the full corpus: "generated from
templates." The 32 hand-authored documents remain the narratively rich,
flagship examples; this batch is deliberately the bulk/long-tail tier.

Every adversarial case from spec section 3 is still built in deliberately at
this larger scale, and cross-referenced against what's actually generated
(e.g. an alert's correct_runbook is looked up in the real runbook set, not
just asserted) rather than assumed correct.
"""

from __future__ import annotations

from meridian.catalog import ServiceEntry
from meridian.corpus.generator import DECOMMISSIONED_SERVICES, FRAGILE_SERVICES
from meridian.corpus.models import CorpusDocument
from meridian.graph import DependencyGraph

# --- Failure category taxonomy ---

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

# Which categories are plausible for a service, keyed by owning team --
# mirrors the layer groupings from the catalog itself.
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


def _pool(catalog: dict[str, ServiceEntry], service: str) -> list[str]:
    return LAYER_POOLS[catalog[service].owner]


# --- Body renderers ---


def _runbook_body(service: str, category: str, catalog: dict[str, ServiceEntry]) -> str:
    info = CATEGORY_INFO[category]
    entry = catalog[service]
    dep_clause = (
        f" Check {entry.depends_on[0]} first -- {service} depends on it directly."
        if entry.depends_on
        else ""
    )
    return (
        f"{service} is showing {info['symptom']}.{dep_clause} Check the {service} dashboard and "
        f"recent deploys via ci-pipeline before assuming the fault is in {service} itself.\n\n"
        f"Likely cause: {info['cause']}.\n\n"
        f"Fix: confirm the cause above against current metrics before acting. Resolve at the source "
        f"rather than restarting {service} -- a restart will not fix {category.replace('_', ' ')} if "
        f"the underlying condition is still present.\n\n"
        f"Blast radius: {entry.blast_radius}"
    )


def _postmortem_body(
    service: str, category: str, catalog: dict[str, ServiceEntry], affected: list[str], incident_number: int
) -> str:
    info = CATEGORY_INFO[category]
    affected_clause = f" This also produced symptoms in {', '.join(affected)}.\n\n" if affected else "\n\n"
    recurrence = (
        f" This is recorded incident #{incident_number} of this type for {service}."
        if incident_number > 1
        else ""
    )
    return (
        f"Summary: {service} experienced {info['symptom']}.{recurrence}{affected_clause}"
        f"Root cause: {info['cause']}.\n\n"
        f"Action items: add direct alerting on this failure mode for {service} rather than relying on "
        f"downstream symptoms to surface it."
    )


def _alert_body(service: str, category: str) -> str:
    info = CATEGORY_INFO[category]
    return (
        f"{service}: {info['symptom']}. Onset was within the last monitoring window -- investigate "
        f"before it breaches SLO further."
    )


# --- Deterministic weighted round-robin over (service, category) pairs ---


def _weighted_order(weights: dict[str, int], length: int) -> list[str]:
    """Largest-remainder-style interleaving: `length` picks from `weights`,
    spread as evenly as each item's weight allows, fully deterministic."""
    counts = {k: 0 for k in weights}
    order = []
    for _ in range(length):
        pick = min(weights, key=lambda k: (counts[k] / weights[k], k))
        order.append(pick)
        counts[pick] += 1
    return order


def _bulk_pairs(
    catalog: dict[str, ServiceEntry],
    count: int,
    weights: dict[str, int],
    exclude: set[tuple[str, str]],
    allow_repeats: bool = False,
) -> list[tuple[str, str]]:
    """`count` (service, category) pairs, weighted round-robin over `weights`'
    services, skipping any pair already in `exclude`. When `allow_repeats` is
    True a service whose pool is exhausted wraps around and reuses categories
    (used for postmortems, where a service can plausibly repeat an incident
    type); otherwise an exhausted service is simply skipped for the rest of
    the run (used for runbooks, where an exact duplicate (service, category)
    would just be redundant reference material).
    """
    service_order = _weighted_order(weights, count * 4)
    pool_index = {s: 0 for s in weights}
    seen: set[tuple[str, str]] = set(exclude)
    pairs: list[tuple[str, str]] = []

    for service in service_order:
        if len(pairs) >= count:
            break
        pool = _pool(catalog, service)
        idx = pool_index[service]
        if idx >= len(pool):
            if not allow_repeats:
                continue
            pool_index[service] = 0
            idx = 0
        category = pool[idx]
        pool_index[service] += 1
        key = (service, category)
        if key in seen and not allow_repeats:
            continue
        seen.add(key)
        pairs.append(key)

    return pairs


# --- Runbooks: 10 near-duplicate pairs (20) + 8 stale (4 decommissioned x 2) + 72 bulk = 100 ---

_NEAR_DUP_SPECS = [
    dict(
        service="postgres-primary",
        category="disk_full",
        id_a="wal-bloat",
        id_b="unvacuumed-table",
        cause_a="unshipped WAL segments accumulated after a replica fell behind, filling the data volume",
        fix_a="ship or rotate the backlogged WAL segments, then investigate why the replica fell behind",
        cause_b="a large table was never vacuumed and its dead-tuple bloat filled the data volume",
        fix_b="run a manual VACUUM on the offending table and check autovacuum settings for that table",
    ),
    dict(
        service="llm-gateway",
        category="upstream_timeout",
        id_a="secrets-manager",
        id_b="feature-flags",
        cause_a="secrets-manager failed to rotate the provider API key in time, so requests are being rejected with auth errors",
        fix_a="check secrets-manager for the provider key's rotation status and rotate manually if it's expired",
        cause_b="a feature-flags rollout changed model routing to a provider region that is currently degraded",
        fix_b="roll back the routing flag in feature-flags to the previous known-good region",
    ),
    dict(
        service="auth-service",
        category="5xx_errors",
        id_a="postgres-primary",
        id_b="redis-cache",
        cause_a="postgres-primary is slow or unavailable, so credential lookups are timing out",
        fix_a="check postgres-primary health directly before touching auth-service itself",
        cause_b="redis-cache is evicting session tokens faster than expected, so token validation is failing",
        fix_b="check redis-cache eviction rate and memory headroom before touching auth-service itself",
    ),
    dict(
        service="cart-service",
        category="5xx_errors",
        id_a="pricing-engine",
        id_b="inventory-service",
        cause_a="pricing-engine is timing out, so cart totals cannot be computed",
        fix_a="check pricing-engine health -- cart-service has no fallback pricing path",
        cause_b="inventory-service is timing out, so stock checks on add-to-cart are failing",
        fix_b="check inventory-service health -- cart-service cannot confirm availability without it",
    ),
    dict(
        service="inventory-service",
        category="5xx_errors",
        id_a="postgres-primary",
        id_b="redis-cache",
        cause_a="postgres-primary is rejecting writes, so stock updates cannot commit",
        fix_a="check postgres-primary write availability directly",
        cause_b="redis-cache is unavailable, so cached stock reads are falling through to an overloaded database path",
        fix_b="check redis-cache availability -- inventory-service was not designed to run cache-less at current load",
    ),
    dict(
        service="orders-service",
        category="5xx_errors",
        id_a="postgres-primary",
        id_b="notification-service",
        cause_a="postgres-primary is rejecting writes, so order state transitions cannot commit",
        fix_a="check postgres-primary write availability directly",
        cause_b="notification-service is timing out on a synchronous confirmation call that should be async",
        fix_b="check notification-service health; consider making this call fire-and-forget if it recurs",
    ),
    dict(
        service="notification-service",
        category="third_party_outage",
        id_a="twilio-sms",
        id_b="sendgrid-email",
        cause_a="twilio-sms is degraded, so SMS notifications are failing to send",
        fix_a="check status.twilio.com; there is no internal fix while the provider is degraded",
        cause_b="sendgrid-email is degraded, so email notifications are failing to send",
        fix_b="check SendGrid's status page; there is no internal fix while the provider is degraded",
    ),
    dict(
        service="search-service",
        category="5xx_errors",
        id_a="postgres-replica",
        id_b="redis-cache",
        cause_a="postgres-replica is unavailable, so search cannot fall back to an uncached query",
        fix_a="check postgres-replica health directly",
        cause_b="redis-cache is unavailable, so every query is falling through to the replica at once",
        fix_b="check redis-cache health directly before assuming the replica itself is overloaded",
    ),
    dict(
        service="user-profile",
        category="5xx_errors",
        id_a="postgres-primary",
        id_b="session-store",
        cause_a="postgres-primary is slow, so profile reads are timing out",
        fix_a="check postgres-primary health directly",
        cause_b="session-store is rejecting session lookups, so profile requests can't be authorized",
        fix_b="check session-store health directly",
    ),
    dict(
        service="warehouse-etl",
        category="job_failure",
        id_a="postgres-replica",
        id_b="s3-storage",
        cause_a="postgres-replica was unreachable during the job's extract phase",
        fix_a="check postgres-replica availability during the job's scheduled window and rerun",
        cause_b="s3-storage rejected writes during the job's load phase",
        fix_b="check s3-storage access and quota, then rerun the job from the load phase",
    ),
]


def _generate_near_dup_runbooks() -> list[CorpusDocument]:
    docs = []
    for spec in _NEAR_DUP_SPECS:
        service, category = spec["service"], spec["category"]
        symptom = CATEGORY_INFO[category]["symptom"]
        shared_intro = (
            f"{service} is showing {symptom}. Check the {service} dashboard for error rate and "
            f"latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.\n\n"
        )
        for variant, cause_key, fix_key in (("a", "cause_a", "fix_a"), ("b", "cause_b", "fix_b")):
            suffix = spec[f"id_{variant}"]
            docs.append(
                CorpusDocument(
                    doc_id=f"runbook-{service}-{category}-{suffix}",
                    doc_type="runbook",
                    title=f"{service}: {category.replace('_', ' ')} ({suffix} root cause)",
                    services=[service],
                    metadata={"root_cause_category": f"{category}__{suffix}"},
                    body=shared_intro + f"Root cause: {spec[cause_key]}.\n\nFix: {spec[fix_key]}.",
                )
            )
    return docs


def _generate_stale_runbooks() -> list[CorpusDocument]:
    replacements = {
        "checkout-monolith-v1": "checkout-api",
        "varnish-cache-cluster": "cdn-config",
        "legacy-recommendation-svc-v1": "recommendation-engine",
        "warehouse-mainframe-v1": "warehouse-api",
        "sms-gateway-v1": "notification-service",
    }
    docs = []
    for decommissioned in DECOMMISSIONED_SERVICES[2:]:  # first two already covered in generator.py
        replacement = replacements[decommissioned]
        for i, angle in enumerate(["elevated error rate", "manual restart procedure"], start=1):
            docs.append(
                CorpusDocument(
                    doc_id=f"runbook-{decommissioned}-{i}",
                    doc_type="runbook",
                    title=f"{decommissioned}: {angle}",
                    services=[decommissioned],
                    metadata={"root_cause_category": "stale", "stale_reference": decommissioned},
                    body=(
                        f"If {decommissioned} shows {angle}, SSH into its hosts and check the "
                        f"application logs directly; restart via the legacy deploy tool if needed.\n\n"
                        f"[This runbook predates the migration to {replacement} and was never removed. "
                        f"{decommissioned} no longer exists.]"
                    ),
                )
            )
    return docs


def generate_runbooks_v2(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    near_dup = _generate_near_dup_runbooks()
    stale = _generate_stale_runbooks()

    exclude = {(spec["service"], spec["category"]) for spec in _NEAR_DUP_SPECS}
    weights = {s: (3 if s in FRAGILE_SERVICES else 1) for s in catalog}
    bulk_count = 100 - len(near_dup) - len(stale)
    # allow_repeats=False: an exact-duplicate (service, category) runbook adds
    # no reference value, unlike postmortems/alerts where a repeat represents
    # a genuine recurring incident.
    bulk_pairs = _bulk_pairs(catalog, bulk_count, weights, exclude, allow_repeats=False)

    bulk = [
        CorpusDocument(
            doc_id=f"runbook-{service}-{category}",
            doc_type="runbook",
            title=f"{service}: {category.replace('_', ' ')}",
            services=[service],
            metadata={"root_cause_category": category},
            body=_runbook_body(service, category, catalog),
        )
        for service, category in bulk_pairs
    ]

    return [*near_dup, *stale, *bulk]


# --- Postmortems: 2 cascades + weighted bulk (fragile ~40%) = 75 ---


def _cascade_subsets(catalog: dict[str, ServiceEntry]) -> tuple[list[str], list[str]]:
    dependents = sorted(DependencyGraph(catalog).dependents("postgres-primary"))
    assert len(dependents) >= 12, "need at least 12 real dependents to build two non-overlapping cascades"
    return dependents[:6], dependents[6:12]


def generate_postmortems_v2(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    subset_a, subset_b = _cascade_subsets(catalog)

    cascades = [
        CorpusDocument(
            doc_id="postmortem-postgres-primary-connection-pool-cascade",
            doc_type="postmortem",
            title="Postmortem: postgres-primary connection pool cascade",
            services=["postgres-primary", *subset_a],
            metadata={
                "root_cause_service": "postgres-primary",
                "root_cause_category": "connection_pool_exhaustion",
                "affected_services": subset_a,
                "fragile_service": "postgres-primary",
            },
            body=_postmortem_body("postgres-primary", "connection_pool_exhaustion", catalog, subset_a, 1),
        ),
        CorpusDocument(
            doc_id="postmortem-postgres-primary-replication-lag-cascade",
            doc_type="postmortem",
            title="Postmortem: postgres-primary replication lag cascade",
            services=["postgres-primary", *subset_b],
            metadata={
                "root_cause_service": "postgres-primary",
                "root_cause_category": "replication_lag",
                "affected_services": subset_b,
                "fragile_service": "postgres-primary",
            },
            body=_postmortem_body("postgres-primary", "replication_lag", catalog, subset_b, 2),
        ),
    ]

    exclude = {
        ("postgres-primary", "connection_pool_exhaustion"),
        ("postgres-primary", "replication_lag"),
    }
    # Fragile and non-fragile services are drawn as two separately-sized
    # groups rather than one weighted pool: with 3 fragile services competing
    # against 38 others, a single weighted interleave converges far too
    # slowly to hit an exact ~40% share within only 73 bulk documents.
    fragile_target = 28  # + 2 cascades above = 30/75 = 40%
    nonfragile_target = 75 - len(cascades) - fragile_target

    fragile_weights = {s: 1 for s in FRAGILE_SERVICES}
    nonfragile_weights = {s: 1 for s in catalog if s not in FRAGILE_SERVICES}

    bulk_pairs = [
        *_bulk_pairs(catalog, fragile_target, fragile_weights, exclude, allow_repeats=True),
        *_bulk_pairs(catalog, nonfragile_target, nonfragile_weights, exclude, allow_repeats=True),
    ]

    seen_counts: dict[tuple[str, str], int] = {}
    bulk = []
    for service, category in bulk_pairs:
        key = (service, category)
        seen_counts[key] = seen_counts.get(key, 0) + 1
        n = seen_counts[key]
        suffix = f"-{n}" if n > 1 else ""
        bulk.append(
            CorpusDocument(
                doc_id=f"postmortem-{service}-{category}{suffix}",
                doc_type="postmortem",
                title=f"Postmortem: {service} {category.replace('_', ' ')}"
                + (f" (incident #{n})" if n > 1 else ""),
                services=[service],
                metadata={
                    "root_cause_service": service,
                    "root_cause_category": category,
                    "affected_services": [],
                    "fragile_service": service if service in FRAGILE_SERVICES else None,
                },
                body=_postmortem_body(service, category, catalog, [], n),
            )
        )

    return [*cascades, *bulk]


# --- Alerts: cross-referenced against the real runbook set, 50 total ---


def _runbook_lookup(runbooks: list[CorpusDocument]) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for doc in runbooks:
        category = doc.metadata.get("root_cause_category", "")
        if "__" in category or category == "stale":
            continue  # near-dup / stale runbooks are deliberately not a clean match target
        for service in doc.services:
            key = (service, category)
            if key not in lookup:  # first (alphabetically-generated) runbook wins, deterministic
                lookup[key] = doc.doc_id
    return lookup


def generate_alerts_v2(catalog: dict[str, ServiceEntry], all_runbooks: list[CorpusDocument]) -> list[CorpusDocument]:
    lookup = _runbook_lookup(all_runbooks)
    subset_a, _ = _cascade_subsets(catalog)

    cascade_alert = CorpusDocument(
        doc_id="alert-multi-service-5xx-spike-v2",
        doc_type="alert",
        title=f"5xx spike across {len(subset_a)} services simultaneously (recurrence)",
        services=subset_a,
        metadata={
            "root_cause_service": "postgres-primary",
            "root_cause_category": "disk_full",
            "correct_runbook": "runbook-postgres-primary-disk-full",
            "has_matching_runbook": True,
            "affected_services": subset_a,
            "fragile_service": "postgres-primary",
        },
        body=(
            f"Simultaneous 5xx rate increase across {', '.join(subset_a)}, all starting within the "
            "same 60-second window. All depend on postgres-primary, directly or transitively. Matches "
            "the pattern from a previous postgres-primary disk-full incident."
        ),
    )

    used_keys: set[tuple[str, str]] = {("postgres-primary", "disk_full")}
    used_counts: dict[tuple[str, str], int] = {}

    def _matched_group(services: list[str], target: int) -> list[CorpusDocument]:
        # Fragile services only have a handful of distinct matching
        # categories, far fewer than their share of 50 alerts requires --
        # repeats (a recurring incident, same category, same correct
        # runbook) are how a small service group still accounts for many
        # alerts, same idea as a postmortem's "incident #2".
        order = _weighted_order({s: 1 for s in services}, target * 8)
        docs: list[CorpusDocument] = []
        for service in order:
            if len(docs) >= target:
                break
            candidates = [c for c in _pool(catalog, service) if (service, c) in lookup]
            if not candidates:
                continue
            category = min(candidates, key=lambda c: used_counts.get((service, c), 0))
            key = (service, category)
            n = used_counts.get(key, 0) + 1
            used_counts[key] = n
            used_keys.add(key)
            suffix = f"-{n}" if n > 1 else ""
            docs.append(
                CorpusDocument(
                    doc_id=f"alert-{service}-{category}{suffix}",
                    doc_type="alert",
                    title=f"{service}: {CATEGORY_INFO[category]['symptom']}"
                    + (f" (recurrence #{n})" if n > 1 else ""),
                    services=[service],
                    metadata={
                        "root_cause_service": service,
                        "root_cause_category": category,
                        "correct_runbook": lookup[key],
                        "has_matching_runbook": True,
                        "fragile_service": service if service in FRAGILE_SERVICES else None,
                    },
                    body=_alert_body(service, category),
                )
            )
        return docs

    fragile_target = 19  # + 1 cascade above = 20/50 = 40%
    nonfragile_matched_target = 25
    matched = [
        *_matched_group(sorted(FRAGILE_SERVICES), fragile_target),
        *_matched_group(sorted(s for s in catalog if s not in FRAGILE_SERVICES), nonfragile_matched_target),
    ]

    unmatched: list[CorpusDocument] = []
    unmatched_target = 50 - 1 - len(matched)  # 5, kept off fragile services to hold the 40% split exact
    for service in sorted(s for s in catalog if s not in FRAGILE_SERVICES):
        if len(unmatched) >= unmatched_target:
            break
        for category in _pool(catalog, service):
            key = (service, category)
            if key not in lookup and key not in used_keys:
                used_keys.add(key)
                unmatched.append(
                    CorpusDocument(
                        doc_id=f"alert-{service}-{category}-unmatched",
                        doc_type="alert",
                        title=f"{service}: {CATEGORY_INFO[category]['symptom']}",
                        services=[service],
                        metadata={
                            "root_cause_service": service,
                            "root_cause_category": category,
                            "correct_runbook": None,
                            "has_matching_runbook": False,
                            "fragile_service": None,
                        },
                        body=_alert_body(service, category),
                    )
                )
                break

    return [cascade_alert, *matched, *unmatched]


# --- Chat transcripts: 25, each tied to a generated alert ---


def generate_chat_transcripts_v2(alerts: list[CorpusDocument]) -> list[CorpusDocument]:
    speakers = ["priya", "dev", "maya", "sam", "jules", "arun", "lin"]
    docs = []
    for i, alert in enumerate(sorted(alerts, key=lambda a: a.doc_id)[:25]):
        service = alert.services[0]
        category = alert.metadata.get("root_cause_category", "unknown")
        symptom = CATEGORY_INFO.get(category, {}).get("symptom", "a symptom")
        s1, s2 = speakers[i % len(speakers)], speakers[(i + 1) % len(speakers)]
        matched = alert.metadata.get("has_matching_runbook")
        if matched:
            resolution = (
                f"[+9m] @{s1}: found the runbook for this, running the fix now\n"
                f"[+14m] @{s2}: confirmed, back to normal"
            )
        else:
            resolution = (
                f"[+9m] @{s1}: couldn't find a runbook for this exact symptom\n"
                f"[+15m] @{s2}: tracked it down manually, let's write a runbook once this is resolved"
            )
        docs.append(
            CorpusDocument(
                doc_id=f"chat-{alert.doc_id}",
                doc_type="chat_transcript",
                title=f"#incidents: {service} alert discussion",
                services=[service],
                metadata={"root_cause_service": alert.metadata.get("root_cause_service")},
                body=(
                    f"[+0m] @{s1}: paged for {service}, {symptom}\n"
                    f"[+2m] @{s2}: looking now\n"
                    f"[+4m] @{s1}: can confirm, checking dependencies\n"
                    f"{resolution}"
                ),
            )
        )
    return docs


# --- Catalog documents: 15 services rendered as retrievable text ---


def generate_catalog_documents_v2(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    already_rendered = {"postgres-primary", "notification-service"}
    selected = [
        "llm-gateway",
        "checkout-api",
        "stripe-gateway",
        "twilio-sms",
        "sendgrid-email",
        "auth-service",
        "redis-cache",
        "search-service",
        "warehouse-etl",
        "secrets-manager",
        "api-gateway",
        "orders-service",
        "inventory-service",
        "cart-service",
        "catalog-service",
    ]
    assert not (set(selected) & already_rendered), "would duplicate a catalog doc from the first batch"
    assert len(selected) == 15

    docs = []
    for name in selected:
        entry = catalog[name]
        body = (
            f"{entry.description}\n\n"
            f"Owner: {entry.owner}. Tier: {entry.tier}.\n"
            f"Depends on: {', '.join(entry.depends_on) or 'nothing'}.\n"
            f"Depended on by: {', '.join(entry.depended_on_by) or 'nothing'}.\n"
            f"Availability target: {entry.slo.availability}%.\n"
            f"Blast radius: {entry.blast_radius}"
        )
        docs.append(
            CorpusDocument(
                doc_id=f"catalog-entry-{entry.name}",
                doc_type="catalog_entry",
                title=f"Service catalog: {entry.name}",
                services=[entry.name],
                metadata={"tier": entry.tier, "owner": entry.owner},
                body=body,
            )
        )
    return docs


def generate_corpus_v2(catalog: dict[str, ServiceEntry], existing_runbooks: list[CorpusDocument]) -> list[CorpusDocument]:
    runbooks = generate_runbooks_v2(catalog)
    postmortems = generate_postmortems_v2(catalog)
    alerts = generate_alerts_v2(catalog, [*existing_runbooks, *runbooks])
    chats = generate_chat_transcripts_v2(alerts)
    catalog_docs = generate_catalog_documents_v2(catalog)
    return [*runbooks, *postmortems, *alerts, *chats, *catalog_docs]
