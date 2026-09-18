---
doc_id: alert-cascade-postgres-primary-1
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- checkout-api
- ci-pipeline
- config-service
- inventory-service
- mobile-api
- orders-service
metadata:
  root_cause_service: postgres-primary
  root_cause_category: replication_lag
  correct_runbook: runbook-cascade-root-cause-postgres-primary-replication_lag
  has_matching_runbook: true
  affected_services:
  - checkout-api
  - ci-pipeline
  - config-service
  - inventory-service
  - mobile-api
  - orders-service
  fragile_service: postgres-primary
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across checkout-api, ci-pipeline, config-service, inventory-service, mobile-api, orders-service, all starting within the same 60-second window. All depend on postgres-primary, directly or transitively.
