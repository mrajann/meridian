---
doc_id: runbook-baseline-catalog-service-cache_eviction
doc_type: runbook
title: 'catalog-service: cache eviction'
services:
- catalog-service
metadata:
  root_cause_category: cache_eviction
---

catalog-service is showing elevated latency and a rise in cold-cache misses. Check postgres-primary first -- catalog-service depends on it directly. Check the catalog-service dashboard and recent deploys via ci-pipeline before assuming the fault is in catalog-service itself.

Likely cause: an eviction policy or memory limit change is evicting entries faster than expected.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting catalog-service -- a restart will not fix cache eviction if the underlying condition is still present.

Blast radius: Product pages fail to load or show missing/stale data.
