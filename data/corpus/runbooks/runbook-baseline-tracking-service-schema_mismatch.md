---
doc_id: runbook-baseline-tracking-service-schema_mismatch
doc_type: runbook
title: 'tracking-service: schema mismatch'
services:
- tracking-service
metadata:
  root_cause_category: schema_mismatch
---

tracking-service is showing requests failing validation unexpectedly. Check postgres-replica first -- tracking-service depends on it directly. Check the tracking-service dashboard and recent deploys via ci-pipeline before assuming the fault is in tracking-service itself.

Likely cause: a caller is still sending a previous version of the request schema.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting tracking-service -- a restart will not fix schema mismatch if the underlying condition is still present.

Blast radius: Customers see stale or missing tracking status. Shipments still move.
