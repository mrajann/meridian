---
doc_id: alert-cascade-postgres-primary-3
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- shipping-service
- tracking-service
- user-profile
- warehouse-api
- warehouse-etl
- web-frontend
metadata:
  root_cause_service: postgres-primary
  root_cause_category: job_failure
  correct_runbook: runbook-cascade-root-cause-postgres-primary-job_failure
  has_matching_runbook: true
  affected_services:
  - shipping-service
  - tracking-service
  - user-profile
  - warehouse-api
  - warehouse-etl
  - web-frontend
  fragile_service: postgres-primary
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across shipping-service, tracking-service, user-profile, warehouse-api, warehouse-etl, web-frontend, all starting within the same 60-second window. All depend on postgres-primary, directly or transitively.
