---
doc_id: alert-near-dup-shipping-service
doc_type: alert
title: 'shipping-service: an elevated 5xx error rate'
services:
- shipping-service
metadata:
  root_cause_service: shipping-service
  root_cause_category: 5xx_errors__orders-service
  correct_runbook: runbook-shipping-service-orders-service
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

shipping-service: an elevated 5xx error rate. Onset within the last monitoring window.
