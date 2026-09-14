---
doc_id: runbook-pricing-engine-race_condition
doc_type: runbook
title: 'pricing-engine: race condition'
services:
- pricing-engine
metadata:
  root_cause_category: race_condition
---

pricing-engine is showing inconsistent or duplicated state under concurrent load. Check postgres-primary first -- pricing-engine depends on it directly. Check the pricing-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in pricing-engine itself.

Likely cause: two concurrent operations both read stale state before either write committed.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting pricing-engine -- a restart will not fix race condition if the underlying condition is still present.

Blast radius: Checkout may show incorrect prices or fail to price the cart.
