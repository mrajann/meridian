---
doc_id: runbook-baseline-warehouse-etl-replication_lag
doc_type: runbook
title: 'warehouse-etl: replication lag'
services:
- warehouse-etl
metadata:
  root_cause_category: replication_lag
---

warehouse-etl is showing reads returning stale or out-of-date data. Check postgres-replica first -- warehouse-etl depends on it directly. Check the warehouse-etl dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-etl itself.

Likely cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-etl -- a restart will not fix replication lag if the underlying condition is still present.

Blast radius: Analytics and reporting data goes stale. No customer-facing impact.
