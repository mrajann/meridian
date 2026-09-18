---
doc_id: runbook-postgres-primary-wal-bloat
doc_type: runbook
title: 'postgres-primary: writes being refused or new work no longer being accepted
  (wal-bloat root cause)'
services:
- postgres-primary
metadata:
  root_cause_category: disk_full__wal-bloat
---

postgres-primary is showing writes being refused or new work no longer being accepted. Check the postgres-primary dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: unshipped WAL segments accumulated after a replica fell behind, filling the data volume.

Fix: ship or rotate the backlogged WAL segments, then investigate why the replica fell behind.
