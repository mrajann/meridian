---
doc_id: runbook-search-service-third_party_outage
doc_type: runbook
title: 'search-service: third party outage'
services:
- search-service
metadata:
  root_cause_category: third_party_outage
---

search-service is showing requests to an external provider failing or timing out. Check postgres-replica first -- search-service depends on it directly. Check the search-service dashboard and recent deploys via ci-pipeline before assuming the fault is in search-service itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting search-service -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Search returns no or stale results. Browsing by category still works.
