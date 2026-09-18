---
doc_id: alert-near-dup-log-aggregator
doc_type: alert
title: 'log-aggregator: a batch or background job no longer producing fresh output'
services:
- log-aggregator
metadata:
  root_cause_service: log-aggregator
  root_cause_category: job_failure__kafka-broker
  correct_runbook: runbook-log-aggregator-kafka-broker
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

log-aggregator: a batch or background job no longer producing fresh output. Onset within the last monitoring window.
