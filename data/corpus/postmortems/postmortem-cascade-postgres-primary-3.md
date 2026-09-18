---
doc_id: postmortem-cascade-postgres-primary-3
doc_type: postmortem
title: 'Postmortem: postgres-primary cascade (a batch or background job no longer
  producing fresh output)'
services:
- postgres-primary
- shipping-service
- tracking-service
- user-profile
- warehouse-api
- warehouse-etl
- web-frontend
metadata:
  root_cause_service: postgres-primary
  root_cause_category: job_failure
  affected_services:
  - shipping-service
  - tracking-service
  - user-profile
  - warehouse-api
  - warehouse-etl
  - web-frontend
  fragile_service: postgres-primary
  adversarial_case: cascading_failure
---

Summary: postgres-primary experienced a batch or background job no longer producing fresh output. This produced symptoms in 6 dependent services at once: shipping-service, tracking-service, user-profile, warehouse-api, warehouse-etl, web-frontend.

Root cause: the job has been failing without alerting directly on job failure.

On-call for several of the affected services were paged independently before the shared root cause on postgres-primary was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on postgres-primary rather than relying on downstream symptoms to surface a shared root cause.
