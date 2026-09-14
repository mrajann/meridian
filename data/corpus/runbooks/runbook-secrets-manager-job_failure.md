---
doc_id: runbook-secrets-manager-job_failure
doc_type: runbook
title: 'secrets-manager: job failure'
services:
- secrets-manager
metadata:
  root_cause_category: job_failure
---

secrets-manager is showing a batch or background job no longer producing fresh output. Check the secrets-manager dashboard and recent deploys via ci-pipeline before assuming the fault is in secrets-manager itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting secrets-manager -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Services with expiring credentials begin failing auth to their dependencies.
