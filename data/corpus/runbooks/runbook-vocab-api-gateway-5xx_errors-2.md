---
doc_id: runbook-vocab-api-gateway-5xx_errors-2
doc_type: runbook
title: 'api-gateway: server errors elevated'
services:
- api-gateway
metadata:
  root_cause_category: 5xx_errors
  adversarial_case: vocabulary_mismatch
---

api-gateway runbook.

Symptom: server errors elevated.

Fix: address the underlying condition directly on api-gateway -- a restart alone will not resolve this.
