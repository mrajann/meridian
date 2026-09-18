---
doc_id: postmortem-baseline-ci-pipeline-job_failure
doc_type: postmortem
title: 'Postmortem: ci-pipeline job failure'
services:
- ci-pipeline
metadata:
  root_cause_service: ci-pipeline
  root_cause_category: job_failure
  affected_services: []
  fragile_service: null
---

Summary: ci-pipeline experienced a batch or background job no longer producing fresh output.

Root cause: the job has been failing without alerting directly on job failure.

Action items: add direct alerting on this failure mode for ci-pipeline rather than relying on downstream symptoms to surface it.
