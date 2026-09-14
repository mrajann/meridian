---
doc_id: runbook-postgres-replica-lag
doc_type: runbook
title: 'postgres-replica: replication lag'
services:
- postgres-replica
- postgres-primary
metadata:
  root_cause_category: replication_lag
---

postgres-replica is falling behind postgres-primary, causing search-service and analytics-api to serve stale reads. Check replication lag via `pg_stat_replication` on the primary. Common causes: a long-running query on the replica blocking WAL replay, or network saturation between primary and replica.

Fix: kill the blocking query if one exists; if lag is network-driven, it typically self-resolves once traffic drops. This is not a postgres-primary outage -- the primary is healthy and accepting writes normally.
