---
doc_id: runbook-search-service-redis-cache
doc_type: runbook
title: 'search-service: requests to an external provider failing or timing out (redis-cache
  root cause)'
services:
- search-service
metadata:
  root_cause_category: third_party_outage__redis-cache
---

search-service is showing requests to an external provider failing or timing out. Check the search-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is degraded or unavailable, so search-service's calls to it are failing or timing out.

Fix: check redis-cache health directly before touching search-service itself.
