---
doc_id: postmortem-baseline-postgres-primary-job_failure
doc_type: postmortem
title: 'Postmortem: postgres-primary job failure'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: job_failure
  affected_services: []
  fragile_service: postgres-primary
---

Summary: postgres-primary experienced a batch or background job no longer producing fresh output.

Root cause: the job has been failing without alerting directly on job failure.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
