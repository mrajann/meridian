---
doc_id: alert-cascade-redis-cache-5
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- feature-flags
- inventory-service
- llm-gateway
- mobile-api
- orders-service
- pricing-engine
metadata:
  root_cause_service: redis-cache
  root_cause_category: disk_full
  correct_runbook: runbook-cascade-root-cause-redis-cache-disk_full
  has_matching_runbook: true
  affected_services:
  - feature-flags
  - inventory-service
  - llm-gateway
  - mobile-api
  - orders-service
  - pricing-engine
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across feature-flags, inventory-service, llm-gateway, mobile-api, orders-service, pricing-engine, all starting within the same 60-second window. All depend on redis-cache, directly or transitively.
