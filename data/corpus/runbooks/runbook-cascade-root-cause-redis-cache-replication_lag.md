---
doc_id: runbook-cascade-root-cause-redis-cache-replication_lag
doc_type: runbook
title: 'redis-cache: reads returning stale or out-of-date data (cascading)'
services:
- redis-cache
metadata:
  root_cause_category: replication_lag
---

redis-cache is showing reads returning stale or out-of-date data. Because so many services depend on redis-cache directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single redis-cache alert -- treat a burst of simultaneous cross-service errors as one redis-cache incident, not several.

Root cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: resolve the condition on redis-cache directly; the downstream services will recover on their own once it does.
