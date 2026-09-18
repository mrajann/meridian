---
doc_id: runbook-cascade-root-cause-postgres-primary-job_failure
doc_type: runbook
title: 'postgres-primary: a batch or background job no longer producing fresh output
  (cascading)'
services:
- postgres-primary
metadata:
  root_cause_category: job_failure
---

postgres-primary is showing a batch or background job no longer producing fresh output. Because so many services depend on postgres-primary directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single postgres-primary alert -- treat a burst of simultaneous cross-service errors as one postgres-primary incident, not several.

Root cause: the job has been failing without alerting directly on job failure.

Fix: resolve the condition on postgres-primary directly; the downstream services will recover on their own once it does.
