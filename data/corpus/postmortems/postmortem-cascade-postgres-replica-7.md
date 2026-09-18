---
doc_id: postmortem-cascade-postgres-replica-7
doc_type: postmortem
title: 'Postmortem: postgres-replica cascade (requests stalling while waiting on a
  database connection)'
services:
- postgres-replica
- analytics-api
- catalog-service
- chatbot-orchestrator
- mobile-api
- rag-retriever
- recommendation-engine
metadata:
  root_cause_service: postgres-replica
  root_cause_category: connection_pool_exhaustion
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

Summary: postgres-replica experienced requests stalling while waiting on a database connection. This produced symptoms in 6 dependent services at once: analytics-api, catalog-service, chatbot-orchestrator, mobile-api, rag-retriever, recommendation-engine.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

On-call for several of the affected services were paged independently before the shared root cause on postgres-replica was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on postgres-replica rather than relying on downstream symptoms to surface a shared root cause.
