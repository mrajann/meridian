---
doc_id: postmortem-postgres-primary-job_failure-2
doc_type: postmortem
title: 'Postmortem: postgres-primary job failure (incident #2)'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: job_failure
  affected_services: []
  fragile_service: postgres-primary
---

Summary: postgres-primary experienced a batch or background job no longer producing fresh output. This is recorded incident #2 of this type for postgres-primary.

Root cause: the job has been failing without alerting directly on job failure.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
