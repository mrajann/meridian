---
doc_id: postmortem-baseline-feature-flags-job_failure
doc_type: postmortem
title: 'Postmortem: feature-flags job failure'
services:
- feature-flags
metadata:
  root_cause_service: feature-flags
  root_cause_category: job_failure
  affected_services: []
  fragile_service: null
---

Summary: feature-flags experienced a batch or background job no longer producing fresh output.

Root cause: the job has been failing without alerting directly on job failure.

Action items: add direct alerting on this failure mode for feature-flags rather than relying on downstream symptoms to surface it.
