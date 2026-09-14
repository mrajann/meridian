---
doc_id: postmortem-config-service-job_failure
doc_type: postmortem
title: 'Postmortem: config-service job failure'
services:
- config-service
metadata:
  root_cause_service: config-service
  root_cause_category: job_failure
  affected_services: []
  fragile_service: null
---

Summary: config-service experienced a batch or background job no longer producing fresh output.

Root cause: the job has been failing without alerting directly on job failure.

Action items: add direct alerting on this failure mode for config-service rather than relying on downstream symptoms to surface it.
