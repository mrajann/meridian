---
doc_id: alert-baseline-cart-service-race_condition
doc_type: alert
title: 'cart-service: inconsistent or duplicated state under concurrent load'
services:
- cart-service
metadata:
  root_cause_service: cart-service
  root_cause_category: race_condition
  correct_runbook: runbook-vocab-cart-service-race_condition-7
  has_matching_runbook: true
  fragile_service: null
---

cart-service: inconsistent or duplicated state under concurrent load. Onset was within the last monitoring window -- investigate before it breaches SLO further.
