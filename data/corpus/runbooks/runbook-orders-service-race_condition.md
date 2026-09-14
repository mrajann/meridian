---
doc_id: runbook-orders-service-race_condition
doc_type: runbook
title: 'orders-service: race condition'
services:
- orders-service
metadata:
  root_cause_category: race_condition
---

orders-service is showing inconsistent or duplicated state under concurrent load. Check postgres-primary first -- orders-service depends on it directly. Check the orders-service dashboard and recent deploys via ci-pipeline before assuming the fault is in orders-service itself.

Likely cause: two concurrent operations both read stale state before either write committed.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting orders-service -- a restart will not fix race condition if the underlying condition is still present.

Blast radius: Orders can be placed but status updates and cancellations fail.
