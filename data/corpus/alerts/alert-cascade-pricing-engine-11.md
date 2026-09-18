---
doc_id: alert-cascade-pricing-engine-11
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
  root_cause_service: pricing-engine
  root_cause_category: race_condition
  correct_runbook: runbook-cascade-root-cause-pricing-engine-race_condition
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

Simultaneous error-rate increase across cart-service, checkout-api, mobile-api, orders-service, returns-service, shipping-service, all starting within the same 60-second window. All depend on pricing-engine, directly or transitively.
