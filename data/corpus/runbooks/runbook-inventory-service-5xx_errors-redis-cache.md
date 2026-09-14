---
doc_id: runbook-inventory-service-5xx_errors-redis-cache
doc_type: runbook
title: 'inventory-service: 5xx errors (redis-cache root cause)'
services:
- inventory-service
metadata:
  root_cause_category: 5xx_errors__redis-cache
---

inventory-service is showing an elevated 5xx error rate. Check the inventory-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is unavailable, so cached stock reads are falling through to an overloaded database path.

Fix: check redis-cache availability -- inventory-service was not designed to run cache-less at current load.
