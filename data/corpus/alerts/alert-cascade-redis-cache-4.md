---
doc_id: alert-cascade-redis-cache-4
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- api-gateway
- auth-service
- cart-service
- catalog-service
- chatbot-orchestrator
- checkout-api
metadata:
  root_cause_service: redis-cache
  root_cause_category: memory_leak
  correct_runbook: runbook-cascade-root-cause-redis-cache-memory_leak
  has_matching_runbook: true
  affected_services:
  - api-gateway
  - auth-service
  - cart-service
  - catalog-service
  - chatbot-orchestrator
  - checkout-api
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across api-gateway, auth-service, cart-service, catalog-service, chatbot-orchestrator, checkout-api, all starting within the same 60-second window. All depend on redis-cache, directly or transitively.
