---
doc_id: alert-auth-service-connection_pool_exhaustion
doc_type: alert
title: 'auth-service: requests stalling while waiting on a database connection'
services:
- auth-service
metadata:
  root_cause_service: auth-service
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-auth-service-connection_pool_exhaustion
  has_matching_runbook: true
  fragile_service: null
---

auth-service: requests stalling while waiting on a database connection. Onset was within the last monitoring window -- investigate before it breaches SLO further.
