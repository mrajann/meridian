---
doc_id: runbook-vocab-auth-service-connection_pool_exhaustion-18
doc_type: runbook
title: 'auth-service: stale sockets not reaped'
services:
- auth-service
metadata:
  root_cause_category: connection_pool_exhaustion
  adversarial_case: vocabulary_mismatch
---

auth-service runbook.

Symptom: stale sockets not reaped.

Fix: address the underlying condition directly on auth-service -- a restart alone will not resolve this.
