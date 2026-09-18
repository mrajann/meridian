---
doc_id: alert-cascade-inventory-service-10
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- cart-service
- checkout-api
- mobile-api
- orders-service
- returns-service
- shipping-service
metadata:
  root_cause_service: inventory-service
  root_cause_category: 5xx_errors
  correct_runbook: runbook-cascade-root-cause-inventory-service-5xx_errors
  has_matching_runbook: true
  affected_services:
  - cart-service
  - checkout-api
  - mobile-api
  - orders-service
  - returns-service
  - shipping-service
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across cart-service, checkout-api, mobile-api, orders-service, returns-service, shipping-service, all starting within the same 60-second window. All depend on inventory-service, directly or transitively.
