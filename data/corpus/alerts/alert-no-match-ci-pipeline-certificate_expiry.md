---
doc_id: alert-no-match-ci-pipeline-certificate_expiry
doc_type: alert
title: 'ci-pipeline: auth or TLS failures with no code change involved'
services:
- ci-pipeline
metadata:
  root_cause_service: ci-pipeline
  root_cause_category: certificate_expiry
  correct_runbook: null
  has_matching_runbook: false
  fragile_service: null
  adversarial_case: no_matching_runbook
---

ci-pipeline: auth or TLS failures with no code change involved. Onset within the last monitoring window -- investigate before it breaches SLO further.
