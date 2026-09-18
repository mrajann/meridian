---
doc_id: alert-no-match-auth-service-5xx_errors
doc_type: alert
title: 'auth-service: an elevated 5xx error rate'
services:
- auth-service
metadata:
  root_cause_service: auth-service
  root_cause_category: 5xx_errors
  correct_runbook: null
  has_matching_runbook: false
  fragile_service: null
  adversarial_case: no_matching_runbook
---

auth-service: an elevated 5xx error rate. Onset within the last monitoring window -- investigate before it breaches SLO further.
