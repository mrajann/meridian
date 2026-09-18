---
doc_id: runbook-vocab-config-service-job_failure-23
doc_type: runbook
title: 'config-service: errors swallowed without logging'
services:
- config-service
metadata:
  root_cause_category: job_failure
  adversarial_case: vocabulary_mismatch
---

config-service runbook.

Symptom: errors swallowed without logging.

Fix: address the underlying condition directly on config-service -- a restart alone will not resolve this.
