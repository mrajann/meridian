---
doc_id: runbook-postgres-primary-job_failure
doc_type: runbook
title: 'postgres-primary: job failure'
services:
- postgres-primary
metadata:
  root_cause_category: job_failure
---

postgres-primary is showing a batch or background job no longer producing fresh output. Check the postgres-primary dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-primary itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-primary -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: All revenue. Nearly every core-business and platform service reads or writes here.
