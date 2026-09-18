---
doc_id: runbook-baseline-orders-service-deploy_regression
doc_type: runbook
title: 'orders-service: deploy regression'
services:
- orders-service
metadata:
  root_cause_category: deploy_regression
---

orders-service is showing a symptom that started immediately after a deploy. Check postgres-primary first -- orders-service depends on it directly. Check the orders-service dashboard and recent deploys via ci-pipeline before assuming the fault is in orders-service itself.

Likely cause: the most recent deploy introduced a regression.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting orders-service -- a restart will not fix deploy regression if the underlying condition is still present.

Blast radius: Orders can be placed but status updates and cancellations fail.
