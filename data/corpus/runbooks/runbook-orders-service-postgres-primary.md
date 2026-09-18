---
doc_id: runbook-orders-service-postgres-primary
doc_type: runbook
title: 'orders-service: an elevated 5xx error rate (postgres-primary root cause)'
services:
- orders-service
metadata:
  root_cause_category: 5xx_errors__postgres-primary
---

orders-service is showing an elevated 5xx error rate. Check the orders-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is degraded or unavailable, so orders-service's calls to it are failing or timing out.

Fix: check postgres-primary health directly before touching orders-service itself.
