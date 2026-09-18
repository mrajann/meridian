---
doc_id: runbook-ci-pipeline-config-service
doc_type: runbook
title: 'ci-pipeline: a batch or background job no longer producing fresh output (config-service
  root cause)'
services:
- ci-pipeline
metadata:
  root_cause_category: job_failure__config-service
---

ci-pipeline is showing a batch or background job no longer producing fresh output. Check the ci-pipeline dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: config-service is degraded or unavailable, so ci-pipeline's calls to it are failing or timing out.

Fix: check config-service health directly before touching ci-pipeline itself.
