---
doc_id: alert-cascade-postgres-primary-0
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- analytics-api
- api-gateway
- auth-service
- cart-service
- catalog-service
- chatbot-orchestrator
metadata:
  root_cause_service: postgres-primary
  root_cause_category: disk_full
  correct_runbook: runbook-cascade-root-cause-postgres-primary-disk_full
  has_matching_runbook: true
  affected_services:
  - analytics-api
  - api-gateway
  - auth-service
  - cart-service
  - catalog-service
  - chatbot-orchestrator
  fragile_service: postgres-primary
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across analytics-api, api-gateway, auth-service, cart-service, catalog-service, chatbot-orchestrator, all starting within the same 60-second window. All depend on postgres-primary, directly or transitively.
