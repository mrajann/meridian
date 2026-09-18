---
doc_id: runbook-cascade-root-cause-redis-cache-memory_leak
doc_type: runbook
title: 'redis-cache: gradually increasing memory usage and periodic restarts (cascading)'
services:
- redis-cache
metadata:
  root_cause_category: memory_leak
---

redis-cache is showing gradually increasing memory usage and periodic restarts. Because so many services depend on redis-cache directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single redis-cache alert -- treat a burst of simultaneous cross-service errors as one redis-cache incident, not several.

Root cause: a memory leak accumulates until the process is killed for excess memory use and restarts.

Fix: resolve the condition on redis-cache directly; the downstream services will recover on their own once it does.
