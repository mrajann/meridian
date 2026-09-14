---
doc_id: postmortem-auth-service-connection_pool_exhaustion
doc_type: postmortem
title: 'Postmortem: auth-service connection pool exhaustion'
services:
- auth-service
metadata:
  root_cause_service: auth-service
  root_cause_category: connection_pool_exhaustion
  affected_services: []
  fragile_service: null
---

Summary: auth-service experienced requests stalling while waiting on a database connection.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Action items: add direct alerting on this failure mode for auth-service rather than relying on downstream symptoms to surface it.
