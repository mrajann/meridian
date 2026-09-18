---
doc_id: alert-near-dup-llm-gateway
doc_type: alert
title: 'llm-gateway: requests queueing or being rejected outright'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: rate_limit_exhaustion__secrets-manager
  correct_runbook: runbook-llm-gateway-secrets-manager
  has_matching_runbook: true
  fragile_service: llm-gateway
  adversarial_case: near_duplicate_pair
---

llm-gateway: requests queueing or being rejected outright. Onset within the last monitoring window.
