---
doc_id: postmortem-cascade-postgres-primary-2
doc_type: postmortem
title: 'Postmortem: postgres-primary cascade (requests stalling while waiting on a
  database connection)'
services:
- postgres-primary
- postgres-replica
- pricing-engine
- rag-retriever
- recommendation-engine
- returns-service
- search-service
metadata:
  root_cause_service: postgres-primary
  root_cause_category: connection_pool_exhaustion
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

Summary: postgres-primary experienced requests stalling while waiting on a database connection. This produced symptoms in 6 dependent services at once: postgres-replica, pricing-engine, rag-retriever, recommendation-engine, returns-service, search-service.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

On-call for several of the affected services were paged independently before the shared root cause on postgres-primary was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on postgres-primary rather than relying on downstream symptoms to surface a shared root cause.
