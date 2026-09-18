---
doc_id: alert-baseline-postgres-primary-memory_leak
doc_type: alert
title: 'postgres-primary: gradually increasing memory usage and periodic restarts'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: memory_leak
  correct_runbook: runbook-baseline-postgres-primary-memory_leak
  has_matching_runbook: true
  fragile_service: postgres-primary
---

postgres-primary: gradually increasing memory usage and periodic restarts. Onset was within the last monitoring window -- investigate before it breaches SLO further.
