---
doc_id: runbook-baseline-shipping-service-latency_spike
doc_type: runbook
title: 'shipping-service: latency spike'
services:
- shipping-service
metadata:
  root_cause_category: latency_spike
---

shipping-service is showing p99 latency above its SLO target. Check orders-service first -- shipping-service depends on it directly. Check the shipping-service dashboard and recent deploys via ci-pipeline before assuming the fault is in shipping-service itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting shipping-service -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Orders cannot be dispatched for shipping. Order placement unaffected.
