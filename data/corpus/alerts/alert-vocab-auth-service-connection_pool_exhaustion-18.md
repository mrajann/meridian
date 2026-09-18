---
doc_id: alert-vocab-auth-service-connection_pool_exhaustion-18
doc_type: alert
title: 'auth-service: zombie connections piling up'
services:
- auth-service
metadata:
  root_cause_service: auth-service
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-vocab-auth-service-connection_pool_exhaustion-18
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: vocabulary_mismatch
---

auth-service alert: zombie connections piling up. Investigate before this breaches SLO further.
