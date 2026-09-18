---
doc_id: runbook-catalog-service-redis-cache
doc_type: runbook
title: 'catalog-service: an elevated 5xx error rate (redis-cache root cause)'
services:
- catalog-service
metadata:
  root_cause_category: 5xx_errors__redis-cache
---

catalog-service is showing an elevated 5xx error rate. Check the catalog-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is degraded or unavailable, so catalog-service's calls to it are failing or timing out.

Fix: check redis-cache health directly before touching catalog-service itself.
