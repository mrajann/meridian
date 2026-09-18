---
doc_id: postmortem-cascade-redis-cache-4
doc_type: postmortem
title: 'Postmortem: redis-cache cascade (gradually increasing memory usage and periodic
  restarts)'
services:
- redis-cache
- api-gateway
- auth-service
- cart-service
- catalog-service
- chatbot-orchestrator
- checkout-api
metadata:
  root_cause_service: redis-cache
  root_cause_category: memory_leak
  affected_services:
  - api-gateway
  - auth-service
  - cart-service
  - catalog-service
  - chatbot-orchestrator
  - checkout-api
  fragile_service: null
  adversarial_case: cascading_failure
---

Summary: redis-cache experienced gradually increasing memory usage and periodic restarts. This produced symptoms in 6 dependent services at once: api-gateway, auth-service, cart-service, catalog-service, chatbot-orchestrator, checkout-api.

Root cause: a memory leak accumulates until the process is killed for excess memory use and restarts.

On-call for several of the affected services were paged independently before the shared root cause on redis-cache was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on redis-cache rather than relying on downstream symptoms to surface a shared root cause.
