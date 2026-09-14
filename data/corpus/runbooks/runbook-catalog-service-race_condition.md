---
doc_id: runbook-catalog-service-race_condition
doc_type: runbook
title: 'catalog-service: race condition'
services:
- catalog-service
metadata:
  root_cause_category: race_condition
---

catalog-service is showing inconsistent or duplicated state under concurrent load. Check postgres-primary first -- catalog-service depends on it directly. Check the catalog-service dashboard and recent deploys via ci-pipeline before assuming the fault is in catalog-service itself.

Likely cause: two concurrent operations both read stale state before either write committed.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting catalog-service -- a restart will not fix race condition if the underlying condition is still present.

Blast radius: Product pages fail to load or show missing/stale data.
