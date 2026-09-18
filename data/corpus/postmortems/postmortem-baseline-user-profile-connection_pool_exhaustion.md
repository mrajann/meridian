---
doc_id: postmortem-baseline-user-profile-connection_pool_exhaustion
doc_type: postmortem
title: 'Postmortem: user-profile connection pool exhaustion'
services:
- user-profile
metadata:
  root_cause_service: user-profile
  root_cause_category: connection_pool_exhaustion
  affected_services: []
  fragile_service: null
---

Summary: user-profile experienced requests stalling while waiting on a database connection.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Action items: add direct alerting on this failure mode for user-profile rather than relying on downstream symptoms to surface it.
