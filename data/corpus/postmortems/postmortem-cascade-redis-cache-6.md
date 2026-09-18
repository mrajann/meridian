---
doc_id: postmortem-cascade-redis-cache-6
doc_type: postmortem
title: 'Postmortem: redis-cache cascade (reads returning stale or out-of-date data)'
services:
- redis-cache
- rag-retriever
- recommendation-engine
- returns-service
- search-service
- session-store
- shipping-service
metadata:
  root_cause_service: redis-cache
  root_cause_category: replication_lag
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

Summary: redis-cache experienced reads returning stale or out-of-date data. This produced symptoms in 6 dependent services at once: rag-retriever, recommendation-engine, returns-service, search-service, session-store, shipping-service.

Root cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

On-call for several of the affected services were paged independently before the shared root cause on redis-cache was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on redis-cache rather than relying on downstream symptoms to surface a shared root cause.
