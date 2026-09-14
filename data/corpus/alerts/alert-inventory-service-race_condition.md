---
doc_id: alert-inventory-service-race_condition
doc_type: alert
title: 'inventory-service: inconsistent or duplicated state under concurrent load'
services:
- inventory-service
metadata:
  root_cause_service: inventory-service
  root_cause_category: race_condition
  correct_runbook: runbook-inventory-service-oversell
  has_matching_runbook: true
  fragile_service: null
---

inventory-service: inconsistent or duplicated state under concurrent load. Onset was within the last monitoring window -- investigate before it breaches SLO further.
