---
doc_id: alert-multi-service-5xx-spike
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- checkout-api
- orders-service
- cart-service
- auth-service
- catalog-service
- web-frontend
metadata:
  root_cause_service: postgres-primary
  root_cause_category: disk_full
  correct_runbook: runbook-postgres-primary-disk-full
  has_matching_runbook: true
  affected_services:
  - checkout-api
  - orders-service
  - cart-service
  - auth-service
  - catalog-service
  - web-frontend
  fragile_service: postgres-primary
---

Simultaneous 5xx rate increase across checkout-api, orders-service, cart-service, auth-service, catalog-service, web-frontend, all starting within the same 60-second window. No shared deploy across these services in the last 24 hours. All six depend on postgres-primary, directly or transitively.
