---
doc_id: runbook-baseline-checkout-api-latency_spike
doc_type: runbook
title: 'checkout-api: latency spike'
services:
- checkout-api
metadata:
  root_cause_category: latency_spike
---

checkout-api is showing p99 latency above its SLO target. Check auth-service first -- checkout-api depends on it directly. Check the checkout-api dashboard and recent deploys via ci-pipeline before assuming the fault is in checkout-api itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting checkout-api -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: All revenue. Complete outage means no orders can be placed.
