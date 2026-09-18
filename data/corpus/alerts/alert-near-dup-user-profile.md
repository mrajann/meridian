---
doc_id: alert-near-dup-user-profile
doc_type: alert
title: 'user-profile: requests stalling while waiting on a database connection'
services:
- user-profile
metadata:
  root_cause_service: user-profile
  root_cause_category: connection_pool_exhaustion__postgres-primary
  correct_runbook: runbook-user-profile-postgres-primary
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

user-profile: requests stalling while waiting on a database connection. Onset within the last monitoring window.
