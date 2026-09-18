---
doc_id: postmortem-baseline-checkout-api-connection_pool_exhaustion
doc_type: postmortem
title: 'Postmortem: checkout-api connection pool exhaustion'
services:
- checkout-api
metadata:
  root_cause_service: checkout-api
  root_cause_category: connection_pool_exhaustion
  affected_services: []
  fragile_service: null
---

Summary: checkout-api experienced requests stalling while waiting on a database connection.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Action items: add direct alerting on this failure mode for checkout-api rather than relying on downstream symptoms to surface it.
