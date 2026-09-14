---
doc_id: alert-postgres-primary-replication_lag-2
doc_type: alert
title: 'postgres-primary: reads returning stale or out-of-date data (recurrence #2)'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: replication_lag
  correct_runbook: runbook-postgres-replica-lag
  has_matching_runbook: true
  fragile_service: postgres-primary
---

postgres-primary: reads returning stale or out-of-date data. Onset was within the last monitoring window -- investigate before it breaches SLO further.
