---
doc_id: alert-near-dup-cart-service
doc_type: alert
title: 'cart-service: an elevated 5xx error rate'
services:
- cart-service
metadata:
  root_cause_service: cart-service
  root_cause_category: 5xx_errors__redis-cache
  correct_runbook: runbook-cart-service-redis-cache
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

cart-service: an elevated 5xx error rate. Onset within the last monitoring window.
