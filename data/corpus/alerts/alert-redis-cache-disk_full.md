---
doc_id: alert-redis-cache-disk_full
doc_type: alert
title: 'redis-cache: writes being refused or new work no longer being accepted'
services:
- redis-cache
metadata:
  root_cause_service: redis-cache
  root_cause_category: disk_full
  correct_runbook: runbook-redis-cache-disk_full
  has_matching_runbook: true
  fragile_service: null
---

redis-cache: writes being refused or new work no longer being accepted. Onset was within the last monitoring window -- investigate before it breaches SLO further.
