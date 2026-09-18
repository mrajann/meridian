---
doc_id: alert-near-dup-returns-service
doc_type: alert
title: 'returns-service: an elevated 5xx error rate'
services:
- returns-service
metadata:
  root_cause_service: returns-service
  root_cause_category: 5xx_errors__orders-service
  correct_runbook: runbook-returns-service-orders-service
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

returns-service: an elevated 5xx error rate. Onset within the last monitoring window.
