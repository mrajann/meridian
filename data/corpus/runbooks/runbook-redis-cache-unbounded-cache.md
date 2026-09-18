---
doc_id: runbook-redis-cache-unbounded-cache
doc_type: runbook
title: 'redis-cache: gradually increasing memory usage and periodic restarts (unbounded-cache
  root cause)'
services:
- redis-cache
metadata:
  root_cause_category: memory_leak__unbounded-cache
---

redis-cache is showing gradually increasing memory usage and periodic restarts. Check the redis-cache dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: an in-process cache has no eviction policy and grows without bound.

Fix: add a size or TTL bound to the offending cache and redeploy.
