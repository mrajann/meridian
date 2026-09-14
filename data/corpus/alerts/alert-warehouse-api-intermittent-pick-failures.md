---
doc_id: alert-warehouse-api-intermittent-pick-failures
doc_type: alert
title: 'warehouse-api: intermittent pick-confirmation failures'
services:
- warehouse-api
metadata:
  root_cause_service: warehouse-api
  root_cause_category: 5xx_errors
  correct_runbook: runbook-warehouse-api-5xx
  has_matching_runbook: true
  fragile_service: null
---

Warehouse floor scanners are seeing roughly 1-in-20 pick confirmations fail with a 500, unrelated to any specific warehouse location or SKU. inventory-service and postgres-primary both report healthy.
