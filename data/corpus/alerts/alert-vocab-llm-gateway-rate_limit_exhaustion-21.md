---
doc_id: alert-vocab-llm-gateway-rate_limit_exhaustion-21
doc_type: alert
title: 'llm-gateway: requests throttled'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: rate_limit_exhaustion
  correct_runbook: runbook-vocab-llm-gateway-rate_limit_exhaustion-21
  has_matching_runbook: true
  fragile_service: llm-gateway
  adversarial_case: vocabulary_mismatch
---

llm-gateway alert: requests throttled. Investigate before this breaches SLO further.
