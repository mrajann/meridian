---
doc_id: runbook-baseline-inventory-service-cache_eviction
doc_type: runbook
title: 'inventory-service: cache eviction'
services:
- inventory-service
metadata:
  root_cause_category: cache_eviction
---

inventory-service is showing elevated latency and a rise in cold-cache misses. Check postgres-primary first -- inventory-service depends on it directly. Check the inventory-service dashboard and recent deploys via ci-pipeline before assuming the fault is in inventory-service itself.

Likely cause: an eviction policy or memory limit change is evicting entries faster than expected.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting inventory-service -- a restart will not fix cache eviction if the underlying condition is still present.

Blast radius: Risk of overselling out-of-stock items; checkout may show stale availability.
