---
doc_id: postmortem-cascade-postgres-primary-0
doc_type: postmortem
title: 'Postmortem: postgres-primary cascade (writes being refused or new work no
  longer being accepted)'
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
  root_cause_category: disk_full
  affected_services:
  - analytics-api
  - api-gateway
  - auth-service
  - cart-service
  - catalog-service
  - chatbot-orchestrator
  fragile_service: postgres-primary
  adversarial_case: cascading_failure
---

Summary: postgres-primary experienced writes being refused or new work no longer being accepted. This produced symptoms in 6 dependent services at once: analytics-api, api-gateway, auth-service, cart-service, catalog-service, chatbot-orchestrator.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

On-call for several of the affected services were paged independently before the shared root cause on postgres-primary was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on postgres-primary rather than relying on downstream symptoms to surface a shared root cause.
