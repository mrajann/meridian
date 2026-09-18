---
doc_id: runbook-baseline-tracking-service-third_party_outage
doc_type: runbook
title: 'tracking-service: third party outage'
services:
- tracking-service
metadata:
  root_cause_category: third_party_outage
---

tracking-service is showing requests to an external provider failing or timing out. Check postgres-replica first -- tracking-service depends on it directly. Check the tracking-service dashboard and recent deploys via ci-pipeline before assuming the fault is in tracking-service itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting tracking-service -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Customers see stale or missing tracking status. Shipments still move.
