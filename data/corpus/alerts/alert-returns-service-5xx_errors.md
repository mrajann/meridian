---
doc_id: alert-returns-service-5xx_errors
doc_type: alert
title: 'returns-service: an elevated 5xx error rate'
services:
- returns-service
metadata:
  root_cause_service: returns-service
  root_cause_category: 5xx_errors
  correct_runbook: runbook-returns-service-5xx_errors
  has_matching_runbook: true
  fragile_service: null
---

returns-service: an elevated 5xx error rate. Onset was within the last monitoring window -- investigate before it breaches SLO further.
