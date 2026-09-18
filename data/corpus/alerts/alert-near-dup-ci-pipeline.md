---
doc_id: alert-near-dup-ci-pipeline
doc_type: alert
title: 'ci-pipeline: a batch or background job no longer producing fresh output'
services:
- ci-pipeline
metadata:
  root_cause_service: ci-pipeline
  root_cause_category: job_failure__secrets-manager
  correct_runbook: runbook-ci-pipeline-secrets-manager
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

ci-pipeline: a batch or background job no longer producing fresh output. Onset within the last monitoring window.
