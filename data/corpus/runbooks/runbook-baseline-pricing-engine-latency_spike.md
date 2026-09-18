---
doc_id: runbook-baseline-pricing-engine-latency_spike
doc_type: runbook
title: 'pricing-engine: latency spike'
services:
- pricing-engine
metadata:
  root_cause_category: latency_spike
---

pricing-engine is showing p99 latency above its SLO target. Check postgres-primary first -- pricing-engine depends on it directly. Check the pricing-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in pricing-engine itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting pricing-engine -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Checkout may show incorrect prices or fail to price the cart.
