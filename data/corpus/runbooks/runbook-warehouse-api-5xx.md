---
doc_id: runbook-warehouse-api-5xx
doc_type: runbook
title: 'warehouse-api: elevated 5xx rate'
services:
- warehouse-api
metadata:
  root_cause_category: 5xx_errors
---

Warehouse floor systems are getting 5xx responses from warehouse-api when picking or packing orders. Check inventory-service and postgres-primary health first. If both are healthy, check whether a recent warehouse-api deploy changed the pick-confirmation endpoint's request schema -- floor scanner firmware is on a slow update cycle and may still be sending the old schema.

Fix: roll back the deploy if a schema mismatch is confirmed; otherwise treat as a standard 5xx investigation against warehouse-api's own logs.
