---
doc_id: runbook-warehouse-api-5xx_errors
doc_type: runbook
title: 'warehouse-api: 5xx errors'
services:
- warehouse-api
metadata:
  root_cause_category: 5xx_errors
---

warehouse-api is showing an elevated 5xx error rate. Check inventory-service first -- warehouse-api depends on it directly. Check the warehouse-api dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-api itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-api -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Warehouse staff cannot process picks/packs; fulfilment delays.
