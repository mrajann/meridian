---
doc_id: postmortem-baseline-secrets-manager-job_failure
doc_type: postmortem
title: 'Postmortem: secrets-manager job failure'
services:
- secrets-manager
metadata:
  root_cause_service: secrets-manager
  root_cause_category: job_failure
  affected_services: []
  fragile_service: null
---

Summary: secrets-manager experienced a batch or background job no longer producing fresh output.

Root cause: the job has been failing without alerting directly on job failure.

Action items: add direct alerting on this failure mode for secrets-manager rather than relying on downstream symptoms to surface it.
