---
doc_id: runbook-baseline-search-service-quality_degradation
doc_type: runbook
title: 'search-service: quality degradation'
services:
- search-service
metadata:
  root_cause_category: quality_degradation
---

search-service is showing output quality dropping with no traditional error signal. Check postgres-replica first -- search-service depends on it directly. Check the search-service dashboard and recent deploys via ci-pipeline before assuming the fault is in search-service itself.

Likely cause: a routing or model-version change degraded output quality without tripping a health check.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting search-service -- a restart will not fix quality degradation if the underlying condition is still present.

Blast radius: Search returns no or stale results. Browsing by category still works.
