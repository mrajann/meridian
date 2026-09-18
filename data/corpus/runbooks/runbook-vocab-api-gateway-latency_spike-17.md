---
doc_id: runbook-vocab-api-gateway-latency_spike-17
doc_type: runbook
title: 'api-gateway: tail latency degraded'
services:
- api-gateway
metadata:
  root_cause_category: latency_spike
  adversarial_case: vocabulary_mismatch
---

api-gateway runbook.

Symptom: tail latency degraded.

Fix: address the underlying condition directly on api-gateway -- a restart alone will not resolve this.
