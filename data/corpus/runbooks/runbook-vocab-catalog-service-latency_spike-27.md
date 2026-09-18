---
doc_id: runbook-vocab-catalog-service-latency_spike-27
doc_type: runbook
title: 'catalog-service: resource contention from co-located workload'
services:
- catalog-service
metadata:
  root_cause_category: latency_spike
  adversarial_case: vocabulary_mismatch
---

catalog-service runbook.

Symptom: resource contention from co-located workload.

Fix: address the underlying condition directly on catalog-service -- a restart alone will not resolve this.
