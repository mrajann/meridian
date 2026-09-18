---
doc_id: runbook-cascade-root-cause-redis-cache-disk_full
doc_type: runbook
title: 'redis-cache: writes being refused or new work no longer being accepted (cascading)'
services:
- redis-cache
metadata:
  root_cause_category: disk_full
---

redis-cache is showing writes being refused or new work no longer being accepted. Because so many services depend on redis-cache directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single redis-cache alert -- treat a burst of simultaneous cross-service errors as one redis-cache incident, not several.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Fix: resolve the condition on redis-cache directly; the downstream services will recover on their own once it does.
