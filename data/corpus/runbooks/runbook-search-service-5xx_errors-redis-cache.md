---
doc_id: runbook-search-service-5xx_errors-redis-cache
doc_type: runbook
title: 'search-service: 5xx errors (redis-cache root cause)'
services:
- search-service
metadata:
  root_cause_category: 5xx_errors__redis-cache
---

search-service is showing an elevated 5xx error rate. Check the search-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is unavailable, so every query is falling through to the replica at once.

Fix: check redis-cache health directly before assuming the replica itself is overloaded.
