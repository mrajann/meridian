---
doc_id: alert-near-dup-auth-service
doc_type: alert
title: 'auth-service: requests stalling while waiting on a database connection'
services:
- auth-service
metadata:
  root_cause_service: auth-service
  root_cause_category: connection_pool_exhaustion__postgres-primary
  correct_runbook: runbook-auth-service-postgres-primary
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

auth-service: requests stalling while waiting on a database connection. Onset within the last monitoring window.
