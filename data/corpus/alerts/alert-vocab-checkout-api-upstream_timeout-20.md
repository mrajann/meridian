---
doc_id: alert-vocab-checkout-api-upstream_timeout-20
doc_type: alert
title: 'checkout-api: circuit breaker tripped'
services:
- checkout-api
metadata:
  root_cause_service: checkout-api
  root_cause_category: upstream_timeout
  correct_runbook: runbook-vocab-checkout-api-upstream_timeout-20
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: vocabulary_mismatch
---

checkout-api alert: circuit breaker tripped. Investigate before this breaches SLO further.
