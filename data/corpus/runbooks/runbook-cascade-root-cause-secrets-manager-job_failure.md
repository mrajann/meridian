---
doc_id: runbook-cascade-root-cause-secrets-manager-job_failure
doc_type: runbook
title: 'secrets-manager: a batch or background job no longer producing fresh output
  (cascading)'
services:
- secrets-manager
metadata:
  root_cause_category: job_failure
---

secrets-manager is showing a batch or background job no longer producing fresh output. Because so many services depend on secrets-manager directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single secrets-manager alert -- treat a burst of simultaneous cross-service errors as one secrets-manager incident, not several.

Root cause: the job has been failing without alerting directly on job failure.

Fix: resolve the condition on secrets-manager directly; the downstream services will recover on their own once it does.
