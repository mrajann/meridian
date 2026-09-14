---
doc_id: runbook-inventory-service-race_condition
doc_type: runbook
title: 'inventory-service: race condition'
services:
- inventory-service
metadata:
  root_cause_category: race_condition
---

inventory-service is showing inconsistent or duplicated state under concurrent load. Check postgres-primary first -- inventory-service depends on it directly. Check the inventory-service dashboard and recent deploys via ci-pipeline before assuming the fault is in inventory-service itself.

Likely cause: two concurrent operations both read stale state before either write committed.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting inventory-service -- a restart will not fix race condition if the underlying condition is still present.

Blast radius: Risk of overselling out-of-stock items; checkout may show stale availability.
