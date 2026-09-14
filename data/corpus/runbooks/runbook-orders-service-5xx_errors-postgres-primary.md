---
doc_id: runbook-orders-service-5xx_errors-postgres-primary
doc_type: runbook
title: 'orders-service: 5xx errors (postgres-primary root cause)'
services:
- orders-service
metadata:
  root_cause_category: 5xx_errors__postgres-primary
---

orders-service is showing an elevated 5xx error rate. Check the orders-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is rejecting writes, so order state transitions cannot commit.

Fix: check postgres-primary write availability directly.
