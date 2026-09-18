---
doc_id: runbook-baseline-tracking-service-latency_spike
doc_type: runbook
title: 'tracking-service: latency spike'
services:
- tracking-service
metadata:
  root_cause_category: latency_spike
---

tracking-service is showing p99 latency above its SLO target. Check postgres-replica first -- tracking-service depends on it directly. Check the tracking-service dashboard and recent deploys via ci-pipeline before assuming the fault is in tracking-service itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting tracking-service -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Customers see stale or missing tracking status. Shipments still move.
