---
doc_id: runbook-postgres-primary-replication_lag
doc_type: runbook
title: 'postgres-primary: replication lag'
services:
- postgres-primary
metadata:
  root_cause_category: replication_lag
---

postgres-primary is showing reads returning stale or out-of-date data. Check the postgres-primary dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-primary itself.

Likely cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-primary -- a restart will not fix replication lag if the underlying condition is still present.

Blast radius: All revenue. Nearly every core-business and platform service reads or writes here.
