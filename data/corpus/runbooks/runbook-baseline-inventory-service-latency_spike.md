---
doc_id: runbook-baseline-inventory-service-latency_spike
doc_type: runbook
title: 'inventory-service: latency spike'
services:
- inventory-service
metadata:
  root_cause_category: latency_spike
---

inventory-service is showing p99 latency above its SLO target. Check postgres-primary first -- inventory-service depends on it directly. Check the inventory-service dashboard and recent deploys via ci-pipeline before assuming the fault is in inventory-service itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting inventory-service -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Risk of overselling out-of-stock items; checkout may show stale availability.
