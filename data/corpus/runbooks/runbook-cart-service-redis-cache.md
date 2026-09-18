---
doc_id: runbook-cart-service-redis-cache
doc_type: runbook
title: 'cart-service: an elevated 5xx error rate (redis-cache root cause)'
services:
- cart-service
metadata:
  root_cause_category: 5xx_errors__redis-cache
---

cart-service is showing an elevated 5xx error rate. Check the cart-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is degraded or unavailable, so cart-service's calls to it are failing or timing out.

Fix: check redis-cache health directly before touching cart-service itself.
