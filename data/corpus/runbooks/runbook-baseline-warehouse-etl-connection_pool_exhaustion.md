---
doc_id: runbook-baseline-warehouse-etl-connection_pool_exhaustion
doc_type: runbook
title: 'warehouse-etl: connection pool exhaustion'
services:
- warehouse-etl
metadata:
  root_cause_category: connection_pool_exhaustion
---

warehouse-etl is showing requests stalling while waiting on a database connection. Check postgres-replica first -- warehouse-etl depends on it directly. Check the warehouse-etl dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-etl itself.

Likely cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-etl -- a restart will not fix connection pool exhaustion if the underlying condition is still present.

Blast radius: Analytics and reporting data goes stale. No customer-facing impact.
