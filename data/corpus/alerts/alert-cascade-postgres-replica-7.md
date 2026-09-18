---
doc_id: alert-cascade-postgres-replica-7
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- analytics-api
- catalog-service
- chatbot-orchestrator
- mobile-api
- rag-retriever
- recommendation-engine
metadata:
  root_cause_service: postgres-replica
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-cascade-root-cause-postgres-replica-connection_pool_exhaustion
  has_matching_runbook: true
  affected_services:
  - analytics-api
  - catalog-service
  - chatbot-orchestrator
  - mobile-api
  - rag-retriever
  - recommendation-engine
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across analytics-api, catalog-service, chatbot-orchestrator, mobile-api, rag-retriever, recommendation-engine, all starting within the same 60-second window. All depend on postgres-replica, directly or transitively.
