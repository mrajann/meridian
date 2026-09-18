---
doc_id: runbook-baseline-redis-cache-connection_pool_exhaustion
doc_type: runbook
title: 'redis-cache: connection pool exhaustion'
services:
- redis-cache
metadata:
  root_cause_category: connection_pool_exhaustion
---

redis-cache is showing requests stalling while waiting on a database connection. Check the redis-cache dashboard and recent deploys via ci-pipeline before assuming the fault is in redis-cache itself.

Likely cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting redis-cache -- a restart will not fix connection pool exhaustion if the underlying condition is still present.

Blast radius: Elevated latency and error rates across most core-business services.
