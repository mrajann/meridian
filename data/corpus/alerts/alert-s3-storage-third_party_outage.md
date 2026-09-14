---
doc_id: alert-s3-storage-third_party_outage
doc_type: alert
title: 's3-storage: requests to an external provider failing or timing out'
services:
- s3-storage
metadata:
  root_cause_service: s3-storage
  root_cause_category: third_party_outage
  correct_runbook: runbook-s3-storage-third_party_outage
  has_matching_runbook: true
  fragile_service: null
---

s3-storage: requests to an external provider failing or timing out. Onset was within the last monitoring window -- investigate before it breaches SLO further.
