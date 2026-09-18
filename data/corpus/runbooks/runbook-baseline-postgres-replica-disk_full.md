---
doc_id: runbook-baseline-postgres-replica-disk_full
doc_type: runbook
title: 'postgres-replica: disk full'
services:
- postgres-replica
metadata:
  root_cause_category: disk_full
---

postgres-replica is showing writes being refused or new work no longer being accepted. Check postgres-primary first -- postgres-replica depends on it directly. Check the postgres-replica dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-replica itself.

Likely cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-replica -- a restart will not fix disk full if the underlying condition is still present.

Blast radius: Search, analytics, and RAG retrieval see stale or slow reads.
