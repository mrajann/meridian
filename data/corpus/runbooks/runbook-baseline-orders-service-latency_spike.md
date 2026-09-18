---
doc_id: runbook-baseline-orders-service-latency_spike
doc_type: runbook
title: 'orders-service: latency spike'
services:
- orders-service
metadata:
  root_cause_category: latency_spike
---

orders-service is showing p99 latency above its SLO target. Check postgres-primary first -- orders-service depends on it directly. Check the orders-service dashboard and recent deploys via ci-pipeline before assuming the fault is in orders-service itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting orders-service -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Orders can be placed but status updates and cancellations fail.
