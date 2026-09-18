---
doc_id: alert-baseline-postgres-primary-job_failure
doc_type: alert
title: 'postgres-primary: a batch or background job no longer producing fresh output'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: job_failure
  correct_runbook: runbook-cascade-root-cause-postgres-primary-job_failure
  has_matching_runbook: true
  fragile_service: postgres-primary
---

postgres-primary: a batch or background job no longer producing fresh output. Onset was within the last monitoring window -- investigate before it breaches SLO further.
