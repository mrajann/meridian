---
doc_id: runbook-inventory-service-5xx_errors-postgres-primary
doc_type: runbook
title: 'inventory-service: 5xx errors (postgres-primary root cause)'
services:
- inventory-service
metadata:
  root_cause_category: 5xx_errors__postgres-primary
---

inventory-service is showing an elevated 5xx error rate. Check the inventory-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is rejecting writes, so stock updates cannot commit.

Fix: check postgres-primary write availability directly.
