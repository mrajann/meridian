---
doc_id: postmortem-baseline-postgres-primary-connection_pool_exhaustion
doc_type: postmortem
title: 'Postmortem: postgres-primary connection pool exhaustion'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: connection_pool_exhaustion
  affected_services: []
  fragile_service: postgres-primary
---

Summary: postgres-primary experienced requests stalling while waiting on a database connection.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
