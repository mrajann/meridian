---
doc_id: runbook-vocab-auth-service-certificate_expiry-12
doc_type: runbook
title: 'auth-service: certificate expired'
services:
- auth-service
metadata:
  root_cause_category: certificate_expiry
  adversarial_case: vocabulary_mismatch
---

auth-service runbook.

Symptom: certificate expired.

Fix: address the underlying condition directly on auth-service -- a restart alone will not resolve this.
