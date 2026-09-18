---
doc_id: alert-baseline-inventory-service-5xx_errors
doc_type: alert
title: 'inventory-service: an elevated 5xx error rate'
services:
- inventory-service
metadata:
  root_cause_service: inventory-service
  root_cause_category: 5xx_errors
  correct_runbook: runbook-cascade-root-cause-inventory-service-5xx_errors
  has_matching_runbook: true
  fragile_service: null
---

inventory-service: an elevated 5xx error rate. Onset was within the last monitoring window -- investigate before it breaches SLO further.
