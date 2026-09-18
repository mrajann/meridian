---
doc_id: runbook-vocab-kafka-broker-disk_full-25
doc_type: runbook
title: 'kafka-broker: excessive disk IO'
services:
- kafka-broker
metadata:
  root_cause_category: disk_full
  adversarial_case: vocabulary_mismatch
---

kafka-broker runbook.

Symptom: excessive disk IO.

Fix: address the underlying condition directly on kafka-broker -- a restart alone will not resolve this.
