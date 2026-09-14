---
doc_id: alert-multi-service-5xx-spike-v2
doc_type: alert
title: 5xx spike across 6 services simultaneously (recurrence)
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
  correct_runbook: runbook-postgres-primary-disk-full
  has_matching_runbook: true
  affected_services:
  - analytics-api
  - api-gateway
  - auth-service
  - cart-service
  - catalog-service
  - chatbot-orchestrator
  fragile_service: postgres-primary
---

Simultaneous 5xx rate increase across analytics-api, api-gateway, auth-service, cart-service, catalog-service, chatbot-orchestrator, all starting within the same 60-second window. All depend on postgres-primary, directly or transitively. Matches the pattern from a previous postgres-primary disk-full incident.
