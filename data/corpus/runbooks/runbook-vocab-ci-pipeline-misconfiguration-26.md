---
doc_id: runbook-vocab-ci-pipeline-misconfiguration-26
doc_type: runbook
title: 'ci-pipeline: leader election conflict'
services:
- ci-pipeline
metadata:
  root_cause_category: misconfiguration
  adversarial_case: vocabulary_mismatch
---

ci-pipeline runbook.

Symptom: leader election conflict.

Fix: address the underlying condition directly on ci-pipeline -- a restart alone will not resolve this.
