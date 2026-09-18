---
doc_id: runbook-baseline-pricing-engine-deploy_regression
doc_type: runbook
title: 'pricing-engine: deploy regression'
services:
- pricing-engine
metadata:
  root_cause_category: deploy_regression
---

pricing-engine is showing a symptom that started immediately after a deploy. Check postgres-primary first -- pricing-engine depends on it directly. Check the pricing-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in pricing-engine itself.

Likely cause: the most recent deploy introduced a regression.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting pricing-engine -- a restart will not fix deploy regression if the underlying condition is still present.

Blast radius: Checkout may show incorrect prices or fail to price the cart.
