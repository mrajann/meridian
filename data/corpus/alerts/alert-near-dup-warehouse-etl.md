---
doc_id: alert-near-dup-warehouse-etl
doc_type: alert
title: 'warehouse-etl: writes being refused or new work no longer being accepted'
services:
- warehouse-etl
metadata:
  root_cause_service: warehouse-etl
  root_cause_category: disk_full__postgres-replica
  correct_runbook: runbook-warehouse-etl-postgres-replica
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

warehouse-etl: writes being refused or new work no longer being accepted. Onset within the last monitoring window.
