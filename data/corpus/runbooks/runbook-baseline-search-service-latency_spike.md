---
doc_id: runbook-baseline-search-service-latency_spike
doc_type: runbook
title: 'search-service: latency spike'
services:
- search-service
metadata:
  root_cause_category: latency_spike
---

search-service is showing p99 latency above its SLO target. Check postgres-replica first -- search-service depends on it directly. Check the search-service dashboard and recent deploys via ci-pipeline before assuming the fault is in search-service itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting search-service -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Search returns no or stale results. Browsing by category still works.
