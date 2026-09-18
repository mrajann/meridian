---
doc_id: runbook-vocab-analytics-api-connection_pool_exhaustion-0
doc_type: runbook
title: 'analytics-api: database connections maxed out'
services:
- analytics-api
metadata:
  root_cause_category: connection_pool_exhaustion
  adversarial_case: vocabulary_mismatch
---

analytics-api runbook.

Symptom: database connections maxed out.

Fix: address the underlying condition directly on analytics-api -- a restart alone will not resolve this.
