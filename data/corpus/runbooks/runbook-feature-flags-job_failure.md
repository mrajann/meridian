---
doc_id: runbook-feature-flags-job_failure
doc_type: runbook
title: 'feature-flags: job failure'
services:
- feature-flags
metadata:
  root_cause_category: job_failure
---

feature-flags is showing a batch or background job no longer producing fresh output. Check redis-cache first -- feature-flags depends on it directly. Check the feature-flags dashboard and recent deploys via ci-pipeline before assuming the fault is in feature-flags itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting feature-flags -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Flag evaluations fall back to defaults; rollouts and kill switches stop working.
