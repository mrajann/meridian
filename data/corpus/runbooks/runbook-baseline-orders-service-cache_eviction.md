---
doc_id: runbook-baseline-orders-service-cache_eviction
doc_type: runbook
title: 'orders-service: cache eviction'
services:
- orders-service
metadata:
  root_cause_category: cache_eviction
---

orders-service is showing elevated latency and a rise in cold-cache misses. Check postgres-primary first -- orders-service depends on it directly. Check the orders-service dashboard and recent deploys via ci-pipeline before assuming the fault is in orders-service itself.

Likely cause: an eviction policy or memory limit change is evicting entries faster than expected.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting orders-service -- a restart will not fix cache eviction if the underlying condition is still present.

Blast radius: Orders can be placed but status updates and cancellations fail.
