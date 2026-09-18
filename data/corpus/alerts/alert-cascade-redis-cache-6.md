---
doc_id: alert-cascade-redis-cache-6
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- rag-retriever
- recommendation-engine
- returns-service
- search-service
- session-store
- shipping-service
metadata:
  root_cause_service: redis-cache
  root_cause_category: replication_lag
  correct_runbook: runbook-cascade-root-cause-redis-cache-replication_lag
  has_matching_runbook: true
  affected_services:
  - rag-retriever
  - recommendation-engine
  - returns-service
  - search-service
  - session-store
  - shipping-service
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across rag-retriever, recommendation-engine, returns-service, search-service, session-store, shipping-service, all starting within the same 60-second window. All depend on redis-cache, directly or transitively.
