---
doc_id: runbook-redis-cache-disk_full
doc_type: runbook
title: 'redis-cache: disk full'
services:
- redis-cache
metadata:
  root_cause_category: disk_full
---

redis-cache is showing writes being refused or new work no longer being accepted. Check the redis-cache dashboard and recent deploys via ci-pipeline before assuming the fault is in redis-cache itself.

Likely cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting redis-cache -- a restart will not fix disk full if the underlying condition is still present.

Blast radius: Elevated latency and error rates across most core-business services.
