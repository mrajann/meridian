"""Deterministic corpus generator.

Builds a small (~30 doc) but deliberately adversarial corpus: near-duplicate
runbooks, a vocabulary mismatch between an alert and its correct runbook, an
alert with no matching runbook anywhere in the corpus, a postgres-primary
cascade spanning six dependent services, and stale runbooks referencing
decommissioned services. See meridian-spec.md section 3.

Nothing here is randomized -- every document is explicitly authored so the
corpus is identical on every run and every adversarial property can be
asserted directly in tests rather than probabilistically.
"""

from __future__ import annotations

from meridian.catalog import ServiceEntry
from meridian.corpus.models import CorpusDocument
from meridian.graph import DependencyGraph

# The three services the spec calls out as the source of ~40% of incidents.
FRAGILE_SERVICES = {"postgres-primary", "llm-gateway", "notification-service"}

# Services referenced by stale runbooks that no longer exist in the catalog --
# used to build the "stale runbook" adversarial case and to assert, in tests,
# that they really are absent from meridian.catalog.load_catalog().
DECOMMISSIONED_SERVICES = [
    "checkout-monolith-v1",
    "varnish-cache-cluster",
    "legacy-recommendation-svc-v1",
    "warehouse-mainframe-v1",
    "sms-gateway-v1",
]

_CHECKOUT_5XX_INTRO = (
    "checkout-api is returning elevated 5xx rates or p99 latency above its "
    "400ms SLO target. Follow this triage sequence before escalating:\n\n"
    "1. Check the checkout-api dashboard for error rate and latency by endpoint.\n"
    "2. Check recent deploys via ci-pipeline -- roll back if a deploy correlates "
    "with the onset.\n"
    "3. Check upstream dependency health: auth-service, inventory-service, "
    "pricing-engine, postgres-primary, and stripe-gateway.\n"
    "4. Confirm current on-call for payments-platform is aware before taking "
    "any remediation action, since checkout-api is revenue-critical.\n"
    "5. Narrow down which specific upstream dependency is the actual source "
    "before applying a fix -- do not guess."
)


def generate_runbooks() -> list[CorpusDocument]:
    docs = [
        # --- Near-duplicate pair: only one is correct for a given checkout-api alert. ---
        CorpusDocument(
            doc_id="runbook-checkout-5xx-database",
            doc_type="runbook",
            title="checkout-api 5xx: database root cause",
            services=["checkout-api", "postgres-primary"],
            metadata={"root_cause_category": "connection_pool_exhaustion"},
            body=(
                f"{_CHECKOUT_5XX_INTRO}\n\n"
                "Root cause: postgres-primary. Database connections are maxed "
                "out under sustained load, so checkout-api's queries queue "
                "until they time out.\n\n"
                "Fix: check `pg_stat_activity` on postgres-primary against "
                "`max_connections`, then restart the connection pooler and "
                "raise the pool size if needed."
            ),
        ),
        CorpusDocument(
            doc_id="runbook-checkout-5xx-upstream",
            doc_type="runbook",
            title="checkout-api 5xx: upstream payment processor root cause",
            services=["checkout-api", "stripe-gateway"],
            metadata={"root_cause_category": "upstream_payment_timeout"},
            body=(
                f"{_CHECKOUT_5XX_INTRO}\n\n"
                "Root cause: stripe-gateway. The payment processor is slow or "
                "erroring, so checkout-api's own latency and error rate rise "
                "in lockstep.\n\n"
                "Fix: check status.stripe.com and the integration dashboard, "
                "then switch checkout-api to the backup payment processor via "
                "feature-flags if Stripe confirms an incident."
            ),
        ),
        # --- Cascade root cause runbook. ---
        CorpusDocument(
            doc_id="runbook-postgres-primary-disk-full",
            doc_type="runbook",
            title="postgres-primary: disk full",
            services=["postgres-primary"],
            metadata={"root_cause_category": "disk_full"},
            body=(
                "postgres-primary is refusing writes or has stopped accepting "
                "new connections, and every service that depends on it -- "
                "directly or transitively -- starts erroring at once. Check disk "
                "usage on the primary before anything else: `df -h` on the data "
                "volume. WAL buildup from a stalled replica or an oversized "
                "unvacuumed table are the two most common causes.\n\n"
                "Fix: free space immediately (rotate/ship old WAL segments, drop "
                "temp tables) to restore write capacity, then find the actual "
                "growth source before it recurs. Do not restart postgres-primary "
                "to 'fix' disk-full -- that does not free space and adds a "
                "recovery window on top of the outage.\n\n"
                "This will present as simultaneous 5xx alerts across "
                "checkout-api, orders-service, auth-service, and several other "
                "unrelated-looking services -- treat it as one incident, not one "
                "per service."
            ),
        ),
        CorpusDocument(
            doc_id="runbook-postgres-replica-lag",
            doc_type="runbook",
            title="postgres-replica: replication lag",
            services=["postgres-replica", "postgres-primary"],
            metadata={"root_cause_category": "replication_lag"},
            body=(
                "postgres-replica is falling behind postgres-primary, causing "
                "search-service and analytics-api to serve stale reads. Check "
                "replication lag via `pg_stat_replication` on the primary. "
                "Common causes: a long-running query on the replica blocking "
                "WAL replay, or network saturation between primary and replica.\n\n"
                "Fix: kill the blocking query if one exists; if lag is "
                "network-driven, it typically self-resolves once traffic drops. "
                "This is not a postgres-primary outage -- the primary is healthy "
                "and accepting writes normally."
            ),
        ),
        # --- llm-gateway ---
        CorpusDocument(
            doc_id="runbook-llm-gateway-rate-limit",
            doc_type="runbook",
            title="llm-gateway: provider rate limit exhaustion",
            services=["llm-gateway"],
            metadata={"root_cause_category": "rate_limit_exhaustion"},
            body=(
                "llm-gateway is returning 429s or queuing requests for an "
                "extended time. This happens when aggregate request volume "
                "across chatbot-orchestrator, rag-retriever, voicebot-asr, and "
                "recommendation-engine exceeds the provider's per-minute token "
                "or request quota.\n\n"
                "Fix: check the llm-gateway dashboard for per-consumer request "
                "volume to identify which caller spiked. Enable the "
                "degraded-mode feature flag to shed recommendation-engine "
                "traffic first (lowest customer impact), then contact the "
                "provider to request a temporary quota increase if the spike is "
                "expected to continue."
            ),
        ),
        CorpusDocument(
            doc_id="runbook-llm-gateway-quality-degradation",
            doc_type="runbook",
            title="llm-gateway: response quality degradation",
            services=["llm-gateway", "chatbot-orchestrator"],
            metadata={"root_cause_category": "quality_degradation"},
            body=(
                "No errors, no elevated latency, no failed requests -- but "
                "chatbot-orchestrator's responses are getting worse, or "
                "customer complaints about the chatbot are rising. This is "
                "llm-gateway's most distinctive failure mode: the underlying "
                "model or a routing change degrades output quality without "
                "tripping any traditional health check.\n\n"
                "Fix: check llm-gateway's model-version routing config for a "
                "recent change (provider-side model deprecation, a new default "
                "model, or a feature-flag rollout). Roll back the routing "
                "config first and confirm quality recovers before investigating "
                "further -- do not assume this is a rag-retriever grounding "
                "problem until llm-gateway's own routing has been ruled out."
            ),
        ),
        # --- notification-service ---
        CorpusDocument(
            doc_id="runbook-notification-service-delivery-failure",
            doc_type="runbook",
            title="notification-service: delivery failures",
            services=["notification-service", "twilio-sms", "sendgrid-email"],
            metadata={"root_cause_category": "third_party_outage"},
            body=(
                "Customers are not receiving order or shipping notifications. "
                "notification-service itself is almost never the root cause -- "
                "it depends on exactly two third parties, twilio-sms and "
                "sendgrid-email, and a failure in either one presents "
                "identically from notification-service's own metrics (queue "
                "backlog growing, delivery confirmations not coming back).\n\n"
                "Fix: check twilio-sms's and sendgrid-email's public status "
                "pages first. If one is degraded, there is no internal fix -- "
                "confirm notification-service is retrying with backoff rather "
                "than dropping messages, and communicate the expected delay. "
                "Do not page data-platform or restart notification-service "
                "itself unless both providers report healthy."
            ),
        ),
        # --- Other services, single runbook each. ---
        CorpusDocument(
            doc_id="runbook-search-service-5xx",
            doc_type="runbook",
            title="search-service: elevated 5xx rate",
            services=["search-service"],
            metadata={"root_cause_category": "5xx_errors"},
            body=(
                "search-service is returning 5xx responses to a meaningful "
                "fraction of queries. Check postgres-replica and redis-cache "
                "health first, since search-service depends on both. If "
                "neither shows errors, check search-service's own logs for "
                "unhandled exceptions in query parsing.\n\n"
                "Fix: restart the affected search-service pods if the error is "
                "isolated to a subset of instances; if postgres-replica or "
                "redis-cache is unhealthy, resolve that first -- search-service "
                "will recover on its own once its dependencies do."
            ),
        ),
        CorpusDocument(
            doc_id="runbook-inventory-service-oversell",
            doc_type="runbook",
            title="inventory-service: oversell risk",
            services=["inventory-service"],
            metadata={"root_cause_category": "race_condition"},
            body=(
                "Multiple concurrent checkouts reserved the same unit of "
                "low-stock inventory, resulting in an oversold SKU. This is "
                "almost always a race condition in the reservation logic under "
                "load, not a data corruption issue in postgres-primary.\n\n"
                "Fix: identify the affected SKU(s) via the inventory "
                "reconciliation job, cancel or backorder the excess orders "
                "with customer support, and check whether the reservation "
                "path's row-level locking was bypassed by a recent deploy."
            ),
        ),
        CorpusDocument(
            doc_id="runbook-warehouse-api-5xx",
            doc_type="runbook",
            title="warehouse-api: elevated 5xx rate",
            services=["warehouse-api"],
            metadata={"root_cause_category": "5xx_errors"},
            body=(
                "Warehouse floor systems are getting 5xx responses from "
                "warehouse-api when picking or packing orders. Check "
                "inventory-service and postgres-primary health first. If both "
                "are healthy, check whether a recent warehouse-api deploy "
                "changed the pick-confirmation endpoint's request schema -- "
                "floor scanner firmware is on a slow update cycle and may "
                "still be sending the old schema.\n\n"
                "Fix: roll back the deploy if a schema mismatch is confirmed; "
                "otherwise treat as a standard 5xx investigation against "
                "warehouse-api's own logs."
            ),
        ),
        # --- Stale runbooks: reference decommissioned services. ---
        CorpusDocument(
            doc_id="runbook-legacy-monolith-5xx",
            doc_type="runbook",
            title="checkout-monolith-v1: elevated error rate",
            services=["checkout-monolith-v1"],
            metadata={
                "root_cause_category": "5xx_errors",
                "stale_reference": "checkout-monolith-v1",
            },
            body=(
                "checkout-monolith-v1 is returning elevated 5xx rates. Check "
                "the monolith's application server logs on the "
                "checkout-monolith-v1 hosts and restart the affected instances "
                "via the legacy deploy tool.\n\n"
                "[This runbook predates the 2024 migration to checkout-api and "
                "was never removed. checkout-monolith-v1 no longer exists.]"
            ),
        ),
        CorpusDocument(
            doc_id="runbook-varnish-cache-purge",
            doc_type="runbook",
            title="varnish-cache-cluster: manual cache purge",
            services=["varnish-cache-cluster"],
            metadata={
                "root_cause_category": "stale_cache",
                "stale_reference": "varnish-cache-cluster",
            },
            body=(
                "If customers report seeing stale product pages, SSH into the "
                "varnish-cache-cluster nodes and run `varnishadm ban.url .` to "
                "force a full purge.\n\n"
                "[varnish-cache-cluster was decommissioned when the storefront "
                "moved to cloudflare-cdn. Cache purges are now done through "
                "cdn-config.]"
            ),
        ),
    ]
    return docs


def generate_alerts(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    cascade_services = _cascade_affected_services(catalog)

    return [
        CorpusDocument(
            doc_id="alert-checkout-api-p99-latency",
            doc_type="alert",
            title="checkout-api p99 latency 2400ms, threshold 400ms",
            services=["checkout-api"],
            metadata={
                "root_cause_service": "postgres-primary",
                "root_cause_category": "connection_pool_exhaustion",
                "correct_runbook": "runbook-checkout-5xx-database",
                "has_matching_runbook": True,
                "fragile_service": "postgres-primary",
            },
            body=(
                "checkout-api p99 latency 2400ms, threshold 400ms. Error rate "
                "also elevated (4.1%, threshold 1%). Onset was sudden, "
                "coinciding with the start of the flash sale. Application "
                "logs show requests stalled waiting on the database "
                "connection pool -- connection pool exhausted."
            ),
        ),
        CorpusDocument(
            doc_id="alert-chatbot-orchestrator-quality-degraded",
            doc_type="alert",
            title="chatbot-orchestrator: response quality score below threshold",
            services=["chatbot-orchestrator"],
            metadata={
                "root_cause_service": "llm-gateway",
                "root_cause_category": "quality_degradation",
                "correct_runbook": "runbook-llm-gateway-quality-degradation",
                "has_matching_runbook": True,
                "fragile_service": "llm-gateway",
            },
            body=(
                "Automated response-quality scoring for chatbot-orchestrator "
                "dropped from a 4.6 to a 2.9 rolling average over the last two "
                "hours. No increase in error rate, latency, or timeout count. "
                "Customer complaint volume for the support chatbot is rising."
            ),
        ),
        CorpusDocument(
            doc_id="alert-notification-service-sms-failures",
            doc_type="alert",
            title="notification-service: SMS delivery confirmation rate below 50%",
            services=["notification-service"],
            metadata={
                "root_cause_service": "twilio-sms",
                "root_cause_category": "third_party_outage",
                "correct_runbook": "runbook-notification-service-delivery-failure",
                "has_matching_runbook": True,
                "fragile_service": "notification-service",
            },
            body=(
                "notification-service SMS delivery confirmation rate dropped "
                "to 12% over the last 30 minutes, threshold 50%. Email "
                "delivery confirmation rate is unaffected at 98%. Queue depth "
                "for the SMS channel is climbing."
            ),
        ),
        CorpusDocument(
            doc_id="alert-multi-service-5xx-spike",
            doc_type="alert",
            title=f"5xx spike across {len(cascade_services)} services simultaneously",
            services=cascade_services,
            metadata={
                "root_cause_service": "postgres-primary",
                "root_cause_category": "disk_full",
                "correct_runbook": "runbook-postgres-primary-disk-full",
                "has_matching_runbook": True,
                "affected_services": cascade_services,
                "fragile_service": "postgres-primary",
            },
            body=(
                "Simultaneous 5xx rate increase across "
                f"{', '.join(cascade_services)}, all starting within the same "
                "60-second window. No shared deploy across these services in "
                "the last 24 hours. All six depend on postgres-primary, "
                "directly or transitively."
            ),
        ),
        CorpusDocument(
            doc_id="alert-search-service-zero-results",
            doc_type="alert",
            title="search-service: zero-result rate above 15% for a subset of queries",
            services=["search-service"],
            metadata={
                "root_cause_service": "search-service",
                "root_cause_category": "stale_index",
                "correct_runbook": None,
                "has_matching_runbook": False,
                "fragile_service": None,
            },
            body=(
                "search-service is returning zero results for roughly 18% of "
                "queries containing recently-added product terms, while "
                "overall error rate and latency are both normal. Affects "
                "search only -- browsing by category still returns correct "
                "results."
            ),
        ),
        CorpusDocument(
            doc_id="alert-warehouse-api-intermittent-pick-failures",
            doc_type="alert",
            title="warehouse-api: intermittent pick-confirmation failures",
            services=["warehouse-api"],
            metadata={
                "root_cause_service": "warehouse-api",
                "root_cause_category": "5xx_errors",
                "correct_runbook": "runbook-warehouse-api-5xx",
                "has_matching_runbook": True,
                "fragile_service": None,
            },
            body=(
                "Warehouse floor scanners are seeing roughly 1-in-20 pick "
                "confirmations fail with a 500, unrelated to any specific "
                "warehouse location or SKU. inventory-service and "
                "postgres-primary both report healthy."
            ),
        ),
    ]


def generate_postmortems(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    cascade_services = _cascade_affected_services(catalog)

    return [
        CorpusDocument(
            doc_id="postmortem-postgres-primary-disk-full-cascade",
            doc_type="postmortem",
            title="Postmortem: postgres-primary disk-full cascade",
            services=["postgres-primary", *cascade_services],
            metadata={
                "root_cause_service": "postgres-primary",
                "root_cause_category": "disk_full",
                "affected_services": cascade_services,
                "fragile_service": "postgres-primary",
            },
            body=(
                "Summary: postgres-primary's data volume filled up after an "
                f"unvacuumed table grew unbounded, causing writes to be "
                f"refused. {len(cascade_services)} services that depend on "
                f"postgres-primary ({', '.join(cascade_services)}) all began "
                "erroring within the same minute.\n\n"
                "Timeline: on-call for checkout-api, orders-service, and "
                "auth-service were paged independently within two minutes of "
                "each other, and initially treated this as three unrelated "
                "incidents before data-platform on-call identified the shared "
                "root cause on postgres-primary.\n\n"
                "Root cause: disk usage on postgres-primary's data volume "
                "reached 100%, refusing further writes.\n\n"
                "Action items: alert directly on postgres-primary disk usage "
                "at 80% rather than relying on downstream service alerts to "
                "surface a shared database problem."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-llm-gateway-rate-limit-exhaustion",
            doc_type="postmortem",
            title="Postmortem: llm-gateway rate limit exhaustion",
            services=["llm-gateway", "chatbot-orchestrator", "voicebot-asr", "recommendation-engine"],
            metadata={
                "root_cause_service": "llm-gateway",
                "root_cause_category": "rate_limit_exhaustion",
                "affected_services": ["chatbot-orchestrator", "voicebot-asr", "recommendation-engine"],
                "fragile_service": "llm-gateway",
            },
            body=(
                "Summary: a marketing push drove a 3x spike in "
                "recommendation-engine traffic, which consumed enough of "
                "llm-gateway's shared provider quota that chatbot-orchestrator "
                "and voicebot-asr both began queuing and timing out.\n\n"
                "Root cause: llm-gateway has no per-consumer rate limiting of "
                "its own -- it passes the provider's aggregate rate limit "
                "straight through, so one noisy consumer can starve the "
                "others.\n\n"
                "Action items: add per-consumer quotas inside llm-gateway so a "
                "traffic spike in one AI-layer service cannot degrade the "
                "others."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-search-service-stale-index",
            doc_type="postmortem",
            title="Postmortem: search-service stale index causing zero results",
            services=["search-service"],
            metadata={
                "root_cause_service": "search-service",
                "root_cause_category": "stale_index",
                "affected_services": [],
                "fragile_service": None,
            },
            body=(
                "Summary: the nightly search index rebuild silently failed for "
                "three consecutive nights, so newly-added product terms "
                "returned zero results even though the products existed in "
                "catalog-service.\n\n"
                "Root cause: the index rebuild job swallowed an exception "
                "instead of failing loudly, so no alert fired on the job "
                "itself -- the only signal was the customer-facing symptom.\n\n"
                "Note: no runbook existed for 'search returns zero results "
                "with no errors' at the time of this incident -- the on-call "
                "engineer spent the first 40 minutes checking search-service-5xx, "
                "which does not apply here since no errors were being thrown. "
                "Action items: write a dedicated runbook for this failure mode, "
                "and alert on index rebuild job failure directly."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-inventory-service-oversell",
            doc_type="postmortem",
            title="Postmortem: inventory-service oversell during flash sale",
            services=["inventory-service"],
            metadata={
                "root_cause_service": "inventory-service",
                "root_cause_category": "race_condition",
                "affected_services": ["cart-service"],
                "fragile_service": None,
            },
            body=(
                "Summary: a limited-stock item was oversold by 40 units during "
                "a flash sale due to a race condition in stock reservation.\n\n"
                "Root cause: two concurrent reservation requests for the same "
                "SKU both read the pre-decrement stock count before either "
                "write committed, allowing both to reserve the last unit.\n\n"
                "Action items: move stock reservation to a single atomic "
                "decrement query instead of read-then-write."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-warehouse-api-pick-confirmation-bug",
            doc_type="postmortem",
            title="Postmortem: warehouse-api pick-confirmation schema mismatch",
            services=["warehouse-api"],
            metadata={
                "root_cause_service": "warehouse-api",
                "root_cause_category": "schema_mismatch",
                "affected_services": [],
                "fragile_service": None,
            },
            body=(
                "Summary: a subset of warehouse floor scanners running "
                "outdated firmware sent pick confirmations in a schema that a "
                "recent warehouse-api deploy no longer accepted, causing "
                "intermittent 500s.\n\n"
                "Root cause: the deploy assumed all scanners had received a "
                "firmware update that was, in practice, only partially rolled "
                "out across warehouses.\n\n"
                "Action items: version the pick-confirmation endpoint and "
                "support the previous schema for one full firmware rollout "
                "cycle."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-secrets-manager-cert-expiry",
            doc_type="postmortem",
            title="Postmortem: expired certificate causes auth-service failures",
            services=["secrets-manager", "auth-service"],
            metadata={
                "root_cause_service": "secrets-manager",
                "root_cause_category": "certificate_expiry",
                "affected_services": ["auth-service"],
                "fragile_service": None,
            },
            body=(
                "Summary: auth-service began rejecting all login attempts when "
                "a TLS certificate issued by secrets-manager expired without "
                "being auto-rotated.\n\n"
                "Root cause: the certificate's auto-rotation policy was "
                "configured for a 90-day cycle, but the certificate itself was "
                "issued with only a 60-day validity, so rotation ran 30 days "
                "too late.\n\n"
                "Action items: alert on certificate expiry directly, "
                "independent of the configured rotation cycle, and audit all "
                "other certificates issued by secrets-manager for the same "
                "mismatch."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-api-gateway-rate-limit-misconfig",
            doc_type="postmortem",
            title="Postmortem: api-gateway rate limit blocks legitimate traffic",
            services=["api-gateway"],
            metadata={
                "root_cause_service": "api-gateway",
                "root_cause_category": "misconfiguration",
                "affected_services": ["web-frontend", "mobile-api"],
                "fragile_service": None,
            },
            body=(
                "Summary: a rate-limit config change intended to target a "
                "single abusive IP range instead matched a much broader CIDR "
                "block, blocking a portion of legitimate customer traffic.\n\n"
                "Root cause: the CIDR block in the rate-limit rule was copied "
                "from an incident runbook example rather than the actual "
                "abusive range identified in that incident.\n\n"
                "Action items: require a dry-run mode for rate-limit rule "
                "changes that reports matched traffic volume before the rule "
                "goes live."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-cdn-config-bad-redirect-rule",
            doc_type="postmortem",
            title="Postmortem: cdn-config bad redirect rule causes 404s",
            services=["cdn-config", "cloudflare-cdn"],
            metadata={
                "root_cause_service": "cdn-config",
                "root_cause_category": "misconfiguration",
                "affected_services": ["web-frontend"],
                "fragile_service": None,
            },
            body=(
                "Summary: a redirect rule pushed to cloudflare-cdn to "
                "deprecate an old URL pattern had an overly broad regex, "
                "causing 404s for a set of currently-valid product URLs.\n\n"
                "Root cause: the regex was tested against a handful of sample "
                "URLs but not against the full corpus of currently-active "
                "product URL patterns.\n\n"
                "Action items: require redirect rule changes to run against a "
                "sample of live traffic in a shadow mode before taking effect."
            ),
        ),
        CorpusDocument(
            doc_id="postmortem-session-store-eviction-storm",
            doc_type="postmortem",
            title="Postmortem: session-store eviction storm forces mass logout",
            services=["session-store", "redis-cache"],
            metadata={
                "root_cause_service": "session-store",
                "root_cause_category": "cache_eviction",
                "affected_services": ["user-profile"],
                "fragile_service": None,
            },
            body=(
                "Summary: a memory limit change on the underlying redis-cache "
                "instance triggered an eviction storm on session-store, "
                "logging out a large fraction of active users simultaneously.\n\n"
                "Root cause: session-store shares its redis-cache instance "
                "with other cache consumers, and a routine memory limit "
                "reduction did not account for session-store's actual working "
                "set size.\n\n"
                "Action items: give session-store a dedicated redis-cache "
                "instance rather than sharing capacity with lower-priority "
                "cache consumers."
            ),
        ),
    ]


def generate_chat_transcripts() -> list[CorpusDocument]:
    return [
        CorpusDocument(
            doc_id="chat-postgres-primary-disk-full-cascade",
            doc_type="chat_transcript",
            title="#incidents: multiple 5xx alerts firing",
            services=["postgres-primary", "checkout-api", "orders-service", "auth-service"],
            metadata={"root_cause_service": "postgres-primary"},
            body=(
                "[14:02] @priya: getting paged for checkout-api 5xx, anyone else?\n"
                "[14:02] @dev: yeah orders-service just paged me too\n"
                "[14:03] @priya: weird, unrelated services, must be two separate things\n"
                "[14:04] @dev: auth-service alert just fired as well. this doesn't feel unrelated anymore\n"
                "[14:05] @priya: checking auth-service logs... it's timing out on postgres queries\n"
                "[14:05] @dev: same on my end for checkout-api, queries just hanging\n"
                "[14:06] @maya: pulling up postgres-primary dashboard now\n"
                "[14:07] @maya: disk is at 100%. this is one incident, not three\n"
                "[14:07] @priya: ok stopping my checkout-api-only investigation, following maya's lead\n"
                "[14:08] @maya: freeing space now, will update here"
            ),
        ),
        CorpusDocument(
            doc_id="chat-llm-gateway-quality-degraded",
            doc_type="chat_transcript",
            title="#support-eng: chatbot answers feel off",
            services=["llm-gateway", "chatbot-orchestrator"],
            metadata={"root_cause_service": "llm-gateway"},
            body=(
                "[09:14] @sam: support lead says chatbot answers have felt off since this morning\n"
                "[09:15] @jules: no alerts firing though, error rate and latency both look normal\n"
                "[09:16] @sam: could be rag-retriever returning bad context?\n"
                "[09:20] @jules: checked, retrieval results look fine and relevant\n"
                "[09:24] @sam: quality score dashboard actually is way down, just no alert threshold on it\n"
                "[09:25] @jules: checking llm-gateway routing config... there was a routing change at 07:00\n"
                "[09:26] @jules: rolling back the routing change now\n"
                "[09:35] @sam: quality score climbing back up, looks like that was it"
            ),
        ),
        CorpusDocument(
            doc_id="chat-search-service-zero-results-investigation",
            doc_type="chat_transcript",
            title="#incidents: search returning zero results for some queries",
            services=["search-service"],
            metadata={"root_cause_service": "search-service"},
            body=(
                "[16:40] @arun: search-service alert, zero-result rate up for a subset of queries\n"
                "[16:41] @lin: pulling up search-service-5xx runbook\n"
                "[16:43] @lin: hold on, that runbook is about 5xx errors, we're not seeing any errors at all\n"
                "[16:43] @arun: right, requests are succeeding, just returning empty result sets\n"
                "[16:44] @lin: checked our runbook index, there isn't one for this specific symptom\n"
                "[16:45] @arun: ok, treating this as unfamiliar territory then. checking the index rebuild job logs directly\n"
                "[16:52] @arun: found it, rebuild job has been silently failing for 3 nights\n"
                "[16:53] @lin: let's write a runbook for this once it's resolved so we're not doing this from scratch next time"
            ),
        ),
    ]


def generate_catalog_documents(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    selected = ["postgres-primary", "notification-service"]
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


def _cascade_affected_services(catalog: dict[str, ServiceEntry]) -> list[str]:
    """Six real dependents of postgres-primary, used for the cascade scenario.

    Pulled from the actual dependency graph (not hand-picked in isolation) so
    the cascade stays consistent with whatever increment 2's catalog defines,
    and asserted against DependencyGraph in tests rather than just trusted.
    """
    curated = ["checkout-api", "orders-service", "cart-service", "auth-service", "catalog-service", "web-frontend"]
    dependents = DependencyGraph(catalog).dependents("postgres-primary")
    missing = [s for s in curated if s not in dependents]
    if missing:
        raise ValueError(f"cascade services no longer depend on postgres-primary: {missing}")
    return curated


def generate_corpus(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    return [
        *generate_runbooks(),
        *generate_postmortems(catalog),
        *generate_alerts(catalog),
        *generate_chat_transcripts(),
        *generate_catalog_documents(catalog),
    ]
