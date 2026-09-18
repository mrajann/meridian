---
doc_id: alert-near-dup-pricing-engine
doc_type: alert
title: 'pricing-engine: an elevated 5xx error rate'
services:
- pricing-engine
metadata:
  root_cause_service: pricing-engine
  root_cause_category: 5xx_errors__postgres-primary
  correct_runbook: runbook-pricing-engine-postgres-primary
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

pricing-engine: an elevated 5xx error rate. Onset within the last monitoring window.
