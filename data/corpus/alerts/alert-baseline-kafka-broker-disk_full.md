---
doc_id: alert-baseline-kafka-broker-disk_full
doc_type: alert
title: 'kafka-broker: writes being refused or new work no longer being accepted'
services:
- kafka-broker
metadata:
  root_cause_service: kafka-broker
  root_cause_category: disk_full
  correct_runbook: runbook-vocab-kafka-broker-disk_full-25
  has_matching_runbook: true
  fragile_service: null
---

kafka-broker: writes being refused or new work no longer being accepted. Onset was within the last monitoring window -- investigate before it breaches SLO further.
