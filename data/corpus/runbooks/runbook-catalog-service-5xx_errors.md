---
doc_id: runbook-catalog-service-5xx_errors
doc_type: runbook
title: 'catalog-service: 5xx errors'
services:
- catalog-service
metadata:
  root_cause_category: 5xx_errors
---

catalog-service is showing an elevated 5xx error rate. Check postgres-primary first -- catalog-service depends on it directly. Check the catalog-service dashboard and recent deploys via ci-pipeline before assuming the fault is in catalog-service itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting catalog-service -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Product pages fail to load or show missing/stale data.
