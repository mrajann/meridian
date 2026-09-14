---
doc_id: runbook-pricing-engine-5xx_errors
doc_type: runbook
title: 'pricing-engine: 5xx errors'
services:
- pricing-engine
metadata:
  root_cause_category: 5xx_errors
---

pricing-engine is showing an elevated 5xx error rate. Check postgres-primary first -- pricing-engine depends on it directly. Check the pricing-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in pricing-engine itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting pricing-engine -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Checkout may show incorrect prices or fail to price the cart.
