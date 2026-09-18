---
doc_id: runbook-warehouse-api-postgres-primary
doc_type: runbook
title: 'warehouse-api: an elevated 5xx error rate (postgres-primary root cause)'
services:
- warehouse-api
metadata:
  root_cause_category: 5xx_errors__postgres-primary
---

warehouse-api is showing an elevated 5xx error rate. Check the warehouse-api dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is degraded or unavailable, so warehouse-api's calls to it are failing or timing out.

Fix: check postgres-primary health directly before touching warehouse-api itself.
