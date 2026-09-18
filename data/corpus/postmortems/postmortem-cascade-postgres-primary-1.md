---
doc_id: postmortem-cascade-postgres-primary-1
doc_type: postmortem
title: 'Postmortem: postgres-primary cascade (reads returning stale or out-of-date
  data)'
services:
- postgres-primary
- checkout-api
- ci-pipeline
- config-service
- inventory-service
- mobile-api
- orders-service
metadata:
  root_cause_service: postgres-primary
  root_cause_category: replication_lag
  affected_services:
  - checkout-api
  - ci-pipeline
  - config-service
  - inventory-service
  - mobile-api
  - orders-service
  fragile_service: postgres-primary
  adversarial_case: cascading_failure
---

Summary: postgres-primary experienced reads returning stale or out-of-date data. This produced symptoms in 6 dependent services at once: checkout-api, ci-pipeline, config-service, inventory-service, mobile-api, orders-service.

Root cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

On-call for several of the affected services were paged independently before the shared root cause on postgres-primary was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on postgres-primary rather than relying on downstream symptoms to surface a shared root cause.
