---
doc_id: postmortem-cascade-redis-cache-5
doc_type: postmortem
title: 'Postmortem: redis-cache cascade (writes being refused or new work no longer
  being accepted)'
services:
- redis-cache
- feature-flags
- inventory-service
- llm-gateway
- mobile-api
- orders-service
- pricing-engine
metadata:
  root_cause_service: redis-cache
  root_cause_category: disk_full
  affected_services:
  - feature-flags
  - inventory-service
  - llm-gateway
  - mobile-api
  - orders-service
  - pricing-engine
  fragile_service: null
  adversarial_case: cascading_failure
---

Summary: redis-cache experienced writes being refused or new work no longer being accepted. This produced symptoms in 6 dependent services at once: feature-flags, inventory-service, llm-gateway, mobile-api, orders-service, pricing-engine.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

On-call for several of the affected services were paged independently before the shared root cause on redis-cache was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on redis-cache rather than relying on downstream symptoms to surface a shared root cause.
