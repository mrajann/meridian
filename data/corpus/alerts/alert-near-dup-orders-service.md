---
doc_id: alert-near-dup-orders-service
doc_type: alert
title: 'orders-service: an elevated 5xx error rate'
services:
- orders-service
metadata:
  root_cause_service: orders-service
  root_cause_category: 5xx_errors__postgres-primary
  correct_runbook: runbook-orders-service-postgres-primary
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

orders-service: an elevated 5xx error rate. Onset within the last monitoring window.
