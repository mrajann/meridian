---
doc_id: runbook-vocab-auth-service-cache_eviction-10
doc_type: runbook
title: 'auth-service: eviction rate elevated'
services:
- auth-service
metadata:
  root_cause_category: cache_eviction
  adversarial_case: vocabulary_mismatch
---

auth-service runbook.

Symptom: eviction rate elevated.

Fix: address the underlying condition directly on auth-service -- a restart alone will not resolve this.
