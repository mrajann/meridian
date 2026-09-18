---
doc_id: runbook-baseline-postgres-replica-replication_lag
doc_type: runbook
title: 'postgres-replica: replication lag'
services:
- postgres-replica
metadata:
  root_cause_category: replication_lag
---

postgres-replica is showing reads returning stale or out-of-date data. Check postgres-primary first -- postgres-replica depends on it directly. Check the postgres-replica dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-replica itself.

Likely cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-replica -- a restart will not fix replication lag if the underlying condition is still present.

Blast radius: Search, analytics, and RAG retrieval see stale or slow reads.
