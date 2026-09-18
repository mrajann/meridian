---
doc_id: alert-baseline-postgres-primary-connection_pool_exhaustion-2
doc_type: alert
title: 'postgres-primary: requests stalling while waiting on a database connection
  (recurrence #2)'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-cascade-root-cause-postgres-primary-connection_pool_exhaustion
  has_matching_runbook: true
  fragile_service: postgres-primary
---

postgres-primary: requests stalling while waiting on a database connection. Onset was within the last monitoring window -- investigate before it breaches SLO further.
