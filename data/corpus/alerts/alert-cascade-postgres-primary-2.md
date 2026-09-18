---
doc_id: alert-cascade-postgres-primary-2
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- postgres-replica
- pricing-engine
- rag-retriever
- recommendation-engine
- returns-service
- search-service
metadata:
  root_cause_service: postgres-primary
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-cascade-root-cause-postgres-primary-connection_pool_exhaustion
  has_matching_runbook: true
  affected_services:
  - postgres-replica
  - pricing-engine
  - rag-retriever
  - recommendation-engine
  - returns-service
  - search-service
  fragile_service: postgres-primary
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across postgres-replica, pricing-engine, rag-retriever, recommendation-engine, returns-service, search-service, all starting within the same 60-second window. All depend on postgres-primary, directly or transitively.
