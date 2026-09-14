---
doc_id: alert-postgres-replica-disk_full
doc_type: alert
title: 'postgres-replica: writes being refused or new work no longer being accepted'
services:
- postgres-replica
metadata:
  root_cause_service: postgres-replica
  root_cause_category: disk_full
  correct_runbook: runbook-postgres-replica-disk_full
  has_matching_runbook: true
  fragile_service: null
---

postgres-replica: writes being refused or new work no longer being accepted. Onset was within the last monitoring window -- investigate before it breaches SLO further.
