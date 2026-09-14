---
doc_id: runbook-ci-pipeline-job_failure
doc_type: runbook
title: 'ci-pipeline: job failure'
services:
- ci-pipeline
metadata:
  root_cause_category: job_failure
---

ci-pipeline is showing a batch or background job no longer producing fresh output. Check secrets-manager first -- ci-pipeline depends on it directly. Check the ci-pipeline dashboard and recent deploys via ci-pipeline before assuming the fault is in ci-pipeline itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting ci-pipeline -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Deploys are blocked. No impact to already-running services.
