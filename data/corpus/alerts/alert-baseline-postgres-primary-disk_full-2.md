---
doc_id: alert-baseline-postgres-primary-disk_full-2
doc_type: alert
title: 'postgres-primary: writes being refused or new work no longer being accepted
  (recurrence #2)'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: disk_full
  correct_runbook: runbook-cascade-root-cause-postgres-primary-disk_full
  has_matching_runbook: true
  fragile_service: postgres-primary
---

postgres-primary: writes being refused or new work no longer being accepted. Onset was within the last monitoring window -- investigate before it breaches SLO further.
