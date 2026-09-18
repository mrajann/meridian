---
doc_id: alert-near-dup-catalog-service
doc_type: alert
title: 'catalog-service: an elevated 5xx error rate'
services:
- catalog-service
metadata:
  root_cause_service: catalog-service
  root_cause_category: 5xx_errors__postgres-primary
  correct_runbook: runbook-catalog-service-postgres-primary
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

catalog-service: an elevated 5xx error rate. Onset within the last monitoring window.
