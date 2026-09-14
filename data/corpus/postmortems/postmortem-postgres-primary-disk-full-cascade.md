---
doc_id: postmortem-postgres-primary-disk-full-cascade
doc_type: postmortem
title: 'Postmortem: postgres-primary disk-full cascade'
services:
- postgres-primary
- checkout-api
- orders-service
- cart-service
- auth-service
- catalog-service
- web-frontend
metadata:
  root_cause_service: postgres-primary
  root_cause_category: disk_full
  affected_services:
  - checkout-api
  - orders-service
  - cart-service
  - auth-service
  - catalog-service
  - web-frontend
  fragile_service: postgres-primary
---

Summary: postgres-primary's data volume filled up after an unvacuumed table grew unbounded, causing writes to be refused. 6 services that depend on postgres-primary (checkout-api, orders-service, cart-service, auth-service, catalog-service, web-frontend) all began erroring within the same minute.

Timeline: on-call for checkout-api, orders-service, and auth-service were paged independently within two minutes of each other, and initially treated this as three unrelated incidents before data-platform on-call identified the shared root cause on postgres-primary.

Root cause: disk usage on postgres-primary's data volume reached 100%, refusing further writes.

Action items: alert directly on postgres-primary disk usage at 80% rather than relying on downstream service alerts to surface a shared database problem.
