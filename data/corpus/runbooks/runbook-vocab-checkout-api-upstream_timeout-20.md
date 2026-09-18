---
doc_id: runbook-vocab-checkout-api-upstream_timeout-20
doc_type: runbook
title: 'checkout-api: downstream marked unhealthy'
services:
- checkout-api
metadata:
  root_cause_category: upstream_timeout
  adversarial_case: vocabulary_mismatch
---

checkout-api runbook.

Symptom: downstream marked unhealthy.

Fix: address the underlying condition directly on checkout-api -- a restart alone will not resolve this.
