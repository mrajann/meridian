---
doc_id: postmortem-postgres-primary-replication-lag-cascade
doc_type: postmortem
title: 'Postmortem: postgres-primary replication lag cascade'
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
---

Summary: postgres-primary experienced reads returning stale or out-of-date data. This is recorded incident #2 of this type for postgres-primary. This also produced symptoms in checkout-api, ci-pipeline, config-service, inventory-service, mobile-api, orders-service.

Root cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
