---
doc_id: runbook-auth-service-5xx_errors-redis-cache
doc_type: runbook
title: 'auth-service: 5xx errors (redis-cache root cause)'
services:
- auth-service
metadata:
  root_cause_category: 5xx_errors__redis-cache
---

auth-service is showing an elevated 5xx error rate. Check the auth-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is evicting session tokens faster than expected, so token validation is failing.

Fix: check redis-cache eviction rate and memory headroom before touching auth-service itself.
