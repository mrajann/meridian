---
doc_id: alert-near-dup-secrets-manager
doc_type: alert
title: 'secrets-manager: auth or TLS failures with no code change involved'
services:
- secrets-manager
metadata:
  root_cause_service: secrets-manager
  root_cause_category: certificate_expiry__rotation-failure
  correct_runbook: runbook-secrets-manager-rotation-failure
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

secrets-manager: auth or TLS failures with no code change involved. Onset within the last monitoring window.
