---
doc_id: alert-near-dup-web-frontend
doc_type: alert
title: 'web-frontend: an elevated 5xx error rate'
services:
- web-frontend
metadata:
  root_cause_service: web-frontend
  root_cause_category: 5xx_errors__api-gateway
  correct_runbook: runbook-web-frontend-api-gateway
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

web-frontend: an elevated 5xx error rate. Onset within the last monitoring window.
