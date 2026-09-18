---
doc_id: runbook-vocab-cart-service-race_condition-7
doc_type: runbook
title: 'cart-service: concurrent update conflict'
services:
- cart-service
metadata:
  root_cause_category: race_condition
  adversarial_case: vocabulary_mismatch
---

cart-service runbook.

Symptom: concurrent update conflict.

Fix: address the underlying condition directly on cart-service -- a restart alone will not resolve this.
