---
doc_id: runbook-search-service-5xx_errors-postgres-replica
doc_type: runbook
title: 'search-service: 5xx errors (postgres-replica root cause)'
services:
- search-service
metadata:
  root_cause_category: 5xx_errors__postgres-replica
---

search-service is showing an elevated 5xx error rate. Check the search-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-replica is unavailable, so search cannot fall back to an uncached query.

Fix: check postgres-replica health directly.
