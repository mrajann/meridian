"""Synonym map for the vocabulary-mismatch adversarial case: two phrasings
of the same underlying condition, one used in alert text, the other in
runbook text, chosen so neither contains the other's key term. This is what
makes naive lexical retrieval fail on a genuinely matching document."""

SYNONYM_PAIRS: list[dict[str, str]] = [
    {"category": "connection_pool_exhaustion", "alert_phrase": "connection pool exhausted", "runbook_phrase": "database connections maxed out"},
    {"category": "memory_leak", "alert_phrase": "OOMKilled", "runbook_phrase": "container ran out of memory"},
    {"category": "5xx_errors", "alert_phrase": "5xx spike", "runbook_phrase": "server errors elevated"},
    {"category": "replication_lag", "alert_phrase": "replica falling behind", "runbook_phrase": "replication lag increasing"},
    {"category": "rate_limit_exhaustion", "alert_phrase": "rate limited", "runbook_phrase": "provider quota exceeded"},
    {"category": "quality_degradation", "alert_phrase": "quality score dropped", "runbook_phrase": "output degraded"},
    {"category": "third_party_outage", "alert_phrase": "vendor outage", "runbook_phrase": "third-party provider degraded"},
    {"category": "race_condition", "alert_phrase": "duplicate writes", "runbook_phrase": "concurrent update conflict"},
    {"category": "schema_mismatch", "alert_phrase": "schema validation failed", "runbook_phrase": "request payload rejected"},
    {"category": "misconfiguration", "alert_phrase": "unexpected behavior with no deploy", "runbook_phrase": "config drift detected"},
    {"category": "cache_eviction", "alert_phrase": "cache miss rate up", "runbook_phrase": "eviction rate elevated"},
    {"category": "stale_data", "alert_phrase": "stale results returned", "runbook_phrase": "index not refreshed"},
    {"category": "certificate_expiry", "alert_phrase": "TLS handshake failing", "runbook_phrase": "certificate expired"},
    {"category": "deploy_regression", "alert_phrase": "regression right after deploy", "runbook_phrase": "bad release rolled out"},
    {"category": "job_failure", "alert_phrase": "job not running", "runbook_phrase": "batch process stalled"},
    {"category": "upstream_timeout", "alert_phrase": "upstream call hanging", "runbook_phrase": "downstream dependency unresponsive"},
    {"category": "disk_full", "alert_phrase": "disk pressure", "runbook_phrase": "data volume nearly full"},
    {"category": "latency_spike", "alert_phrase": "p99 breach", "runbook_phrase": "tail latency degraded"},
    {"category": "connection_pool_exhaustion", "alert_phrase": "zombie connections piling up", "runbook_phrase": "stale sockets not reaped"},
    {"category": "job_failure", "alert_phrase": "queue backlog growing", "runbook_phrase": "consumer lag increasing"},
    {"category": "upstream_timeout", "alert_phrase": "circuit breaker tripped", "runbook_phrase": "downstream marked unhealthy"},
    {"category": "rate_limit_exhaustion", "alert_phrase": "requests throttled", "runbook_phrase": "quota ceiling hit"},
    {"category": "misconfiguration", "alert_phrase": "health checks flapping", "runbook_phrase": "readiness probe failing intermittently"},
    {"category": "job_failure", "alert_phrase": "silent failures reported", "runbook_phrase": "errors swallowed without logging"},
    {"category": "latency_spike", "alert_phrase": "cold start latency", "runbook_phrase": "container startup delay"},
    {"category": "disk_full", "alert_phrase": "write amplification", "runbook_phrase": "excessive disk IO"},
    {"category": "misconfiguration", "alert_phrase": "split-brain observed", "runbook_phrase": "leader election conflict"},
    {"category": "latency_spike", "alert_phrase": "noisy neighbor suspected", "runbook_phrase": "resource contention from co-located workload"},
]
