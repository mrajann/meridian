---
doc_id: alert-orders-service-race_condition
doc_type: alert
title: 'orders-service: inconsistent or duplicated state under concurrent load'
services:
- orders-service
metadata:
  root_cause_service: orders-service
  root_cause_category: race_condition
  correct_runbook: runbook-orders-service-race_condition
  has_matching_runbook: true
  fragile_service: null
---

orders-service: inconsistent or duplicated state under concurrent load. Onset was within the last monitoring window -- investigate before it breaches SLO further.
