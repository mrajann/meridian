---
doc_id: runbook-baseline-search-service-stale_data
doc_type: runbook
title: 'search-service: stale data'
services:
- search-service
metadata:
  root_cause_category: stale_data
---

search-service is showing results or dashboards reflecting outdated state with no errors thrown. Check postgres-replica first -- search-service depends on it directly. Check the search-service dashboard and recent deploys via ci-pipeline before assuming the fault is in search-service itself.

Likely cause: a background refresh or index job has been failing silently.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting search-service -- a restart will not fix stale data if the underlying condition is still present.

Blast radius: Search returns no or stale results. Browsing by category still works.
