---
doc_id: runbook-baseline-warehouse-api-third_party_outage
doc_type: runbook
title: 'warehouse-api: third party outage'
services:
- warehouse-api
metadata:
  root_cause_category: third_party_outage
---

warehouse-api is showing requests to an external provider failing or timing out. Check inventory-service first -- warehouse-api depends on it directly. Check the warehouse-api dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-api itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-api -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Warehouse staff cannot process picks/packs; fulfilment delays.
