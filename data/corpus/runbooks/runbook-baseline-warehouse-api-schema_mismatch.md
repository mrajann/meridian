---
doc_id: runbook-baseline-warehouse-api-schema_mismatch
doc_type: runbook
title: 'warehouse-api: schema mismatch'
services:
- warehouse-api
metadata:
  root_cause_category: schema_mismatch
---

warehouse-api is showing requests failing validation unexpectedly. Check inventory-service first -- warehouse-api depends on it directly. Check the warehouse-api dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-api itself.

Likely cause: a caller is still sending a previous version of the request schema.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-api -- a restart will not fix schema mismatch if the underlying condition is still present.

Blast radius: Warehouse staff cannot process picks/packs; fulfilment delays.
