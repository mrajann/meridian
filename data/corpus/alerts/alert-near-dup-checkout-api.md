---
doc_id: alert-near-dup-checkout-api
doc_type: alert
title: 'checkout-api: requests stalling while waiting on a database connection'
services:
- checkout-api
metadata:
  root_cause_service: checkout-api
  root_cause_category: connection_pool_exhaustion__auth-service
  correct_runbook: runbook-checkout-api-auth-service
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

checkout-api: requests stalling while waiting on a database connection. Onset within the last monitoring window.
