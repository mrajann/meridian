---
doc_id: alert-near-dup-tracking-service
doc_type: alert
title: 'tracking-service: an elevated 5xx error rate'
services:
- tracking-service
metadata:
  root_cause_service: tracking-service
  root_cause_category: 5xx_errors__postgres-replica
  correct_runbook: runbook-tracking-service-postgres-replica
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

tracking-service: an elevated 5xx error rate. Onset within the last monitoring window.
