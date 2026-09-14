---
doc_id: postmortem-session-store-connection_pool_exhaustion
doc_type: postmortem
title: 'Postmortem: session-store connection pool exhaustion'
services:
- session-store
metadata:
  root_cause_service: session-store
  root_cause_category: connection_pool_exhaustion
  affected_services: []
  fragile_service: null
---

Summary: session-store experienced requests stalling while waiting on a database connection.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Action items: add direct alerting on this failure mode for session-store rather than relying on downstream symptoms to surface it.
