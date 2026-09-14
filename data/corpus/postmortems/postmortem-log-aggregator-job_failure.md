---
doc_id: postmortem-log-aggregator-job_failure
doc_type: postmortem
title: 'Postmortem: log-aggregator job failure'
services:
- log-aggregator
metadata:
  root_cause_service: log-aggregator
  root_cause_category: job_failure
  affected_services: []
  fragile_service: null
---

Summary: log-aggregator experienced a batch or background job no longer producing fresh output.

Root cause: the job has been failing without alerting directly on job failure.

Action items: add direct alerting on this failure mode for log-aggregator rather than relying on downstream symptoms to surface it.
