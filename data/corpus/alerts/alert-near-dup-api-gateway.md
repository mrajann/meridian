---
doc_id: alert-near-dup-api-gateway
doc_type: alert
title: 'api-gateway: an elevated 5xx error rate'
services:
- api-gateway
metadata:
  root_cause_service: api-gateway
  root_cause_category: 5xx_errors__auth-service
  correct_runbook: runbook-api-gateway-auth-service
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

api-gateway: an elevated 5xx error rate. Onset within the last monitoring window.
