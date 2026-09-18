---
doc_id: alert-near-dup-inventory-service
doc_type: alert
title: 'inventory-service: an elevated 5xx error rate'
services:
- inventory-service
metadata:
  root_cause_service: inventory-service
  root_cause_category: 5xx_errors__postgres-primary
  correct_runbook: runbook-inventory-service-postgres-primary
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

inventory-service: an elevated 5xx error rate. Onset within the last monitoring window.
