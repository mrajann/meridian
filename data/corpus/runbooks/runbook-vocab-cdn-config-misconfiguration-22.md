---
doc_id: runbook-vocab-cdn-config-misconfiguration-22
doc_type: runbook
title: 'cdn-config: readiness probe failing intermittently'
services:
- cdn-config
metadata:
  root_cause_category: misconfiguration
  adversarial_case: vocabulary_mismatch
---

cdn-config runbook.

Symptom: readiness probe failing intermittently.

Fix: address the underlying condition directly on cdn-config -- a restart alone will not resolve this.
