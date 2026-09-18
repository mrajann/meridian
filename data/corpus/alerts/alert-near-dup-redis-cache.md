---
doc_id: alert-near-dup-redis-cache
doc_type: alert
title: 'redis-cache: gradually increasing memory usage and periodic restarts'
services:
- redis-cache
metadata:
  root_cause_service: redis-cache
  root_cause_category: memory_leak__connection-leak
  correct_runbook: runbook-redis-cache-connection-leak
  has_matching_runbook: true
  fragile_service: null
  adversarial_case: near_duplicate_pair
---

redis-cache: gradually increasing memory usage and periodic restarts. Onset within the last monitoring window.
