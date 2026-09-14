---
doc_id: runbook-postgres-primary-disk_full-unvacuumed-table
doc_type: runbook
title: 'postgres-primary: disk full (unvacuumed-table root cause)'
services:
- postgres-primary
metadata:
  root_cause_category: disk_full__unvacuumed-table
---

postgres-primary is showing writes being refused or new work no longer being accepted. Check the postgres-primary dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: a large table was never vacuumed and its dead-tuple bloat filled the data volume.

Fix: run a manual VACUUM on the offending table and check autovacuum settings for that table.
