---
doc_id: runbook-redis-cache-replication_lag
doc_type: runbook
title: 'redis-cache: replication lag'
services:
- redis-cache
metadata:
  root_cause_category: replication_lag
---

redis-cache is showing reads returning stale or out-of-date data. Check the redis-cache dashboard and recent deploys via ci-pipeline before assuming the fault is in redis-cache itself.

Likely cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting redis-cache -- a restart will not fix replication lag if the underlying condition is still present.

Blast radius: Elevated latency and error rates across most core-business services.
