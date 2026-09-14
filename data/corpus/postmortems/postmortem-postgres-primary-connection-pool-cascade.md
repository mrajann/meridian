---
doc_id: postmortem-postgres-primary-connection-pool-cascade
doc_type: postmortem
title: 'Postmortem: postgres-primary connection pool cascade'
services:
- postgres-primary
- analytics-api
- api-gateway
- auth-service
- cart-service
- catalog-service
- chatbot-orchestrator
metadata:
  root_cause_service: postgres-primary
  root_cause_category: connection_pool_exhaustion
  affected_services:
  - analytics-api
  - api-gateway
  - auth-service
  - cart-service
  - catalog-service
  - chatbot-orchestrator
  fragile_service: postgres-primary
---

Summary: postgres-primary experienced requests stalling while waiting on a database connection. This also produced symptoms in analytics-api, api-gateway, auth-service, cart-service, catalog-service, chatbot-orchestrator.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
