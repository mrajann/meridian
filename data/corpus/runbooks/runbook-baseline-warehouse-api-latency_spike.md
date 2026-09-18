---
doc_id: runbook-baseline-warehouse-api-latency_spike
doc_type: runbook
title: 'warehouse-api: latency spike'
services:
- warehouse-api
metadata:
  root_cause_category: latency_spike
---

warehouse-api is showing p99 latency above its SLO target. Check inventory-service first -- warehouse-api depends on it directly. Check the warehouse-api dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-api itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-api -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Warehouse staff cannot process picks/packs; fulfilment delays.
