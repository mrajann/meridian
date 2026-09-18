---
doc_id: runbook-vocab-llm-gateway-rate_limit_exhaustion-21
doc_type: runbook
title: 'llm-gateway: quota ceiling hit'
services:
- llm-gateway
metadata:
  root_cause_category: rate_limit_exhaustion
  adversarial_case: vocabulary_mismatch
---

llm-gateway runbook.

Symptom: quota ceiling hit.

Fix: address the underlying condition directly on llm-gateway -- a restart alone will not resolve this.
