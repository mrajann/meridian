---
doc_id: runbook-tracking-service-5xx_errors
doc_type: runbook
title: 'tracking-service: 5xx errors'
services:
- tracking-service
metadata:
  root_cause_category: 5xx_errors
---

tracking-service is showing an elevated 5xx error rate. Check postgres-replica first -- tracking-service depends on it directly. Check the tracking-service dashboard and recent deploys via ci-pipeline before assuming the fault is in tracking-service itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting tracking-service -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Customers see stale or missing tracking status. Shipments still move.
