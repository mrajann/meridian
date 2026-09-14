---
doc_id: alert-postgres-primary-connection_pool_exhaustion
doc_type: alert
title: 'postgres-primary: requests stalling while waiting on a database connection'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-checkout-5xx-database
  has_matching_runbook: true
  fragile_service: postgres-primary
---

postgres-primary: requests stalling while waiting on a database connection. Onset was within the last monitoring window -- investigate before it breaches SLO further.
