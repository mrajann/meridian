---
doc_id: runbook-inventory-service-redis-cache
doc_type: runbook
title: 'inventory-service: an elevated 5xx error rate (redis-cache root cause)'
services:
- inventory-service
metadata:
  root_cause_category: 5xx_errors__redis-cache
---

inventory-service is showing an elevated 5xx error rate. Check the inventory-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is degraded or unavailable, so inventory-service's calls to it are failing or timing out.

Fix: check redis-cache health directly before touching inventory-service itself.
