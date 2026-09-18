---
doc_id: alert-near-dup-postgres-primary
doc_type: alert
title: 'postgres-primary: writes being refused or new work no longer being accepted'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: disk_full__wal-bloat
  correct_runbook: runbook-postgres-primary-wal-bloat
  has_matching_runbook: true
  fragile_service: postgres-primary
  adversarial_case: near_duplicate_pair
---

postgres-primary: writes being refused or new work no longer being accepted. Onset within the last monitoring window.
