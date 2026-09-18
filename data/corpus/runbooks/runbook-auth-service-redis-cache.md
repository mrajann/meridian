---
doc_id: runbook-auth-service-redis-cache
doc_type: runbook
title: 'auth-service: requests stalling while waiting on a database connection (redis-cache
  root cause)'
services:
- auth-service
metadata:
  root_cause_category: connection_pool_exhaustion__redis-cache
---

auth-service is showing requests stalling while waiting on a database connection. Check the auth-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is degraded or unavailable, so auth-service's calls to it are failing or timing out.

Fix: check redis-cache health directly before touching auth-service itself.
