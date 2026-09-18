---
doc_id: runbook-vocab-analytics-api-memory_leak-1
doc_type: runbook
title: 'analytics-api: container ran out of memory'
services:
- analytics-api
metadata:
  root_cause_category: memory_leak
  adversarial_case: vocabulary_mismatch
---

analytics-api runbook.

Symptom: container ran out of memory.

Fix: address the underlying condition directly on analytics-api -- a restart alone will not resolve this.
