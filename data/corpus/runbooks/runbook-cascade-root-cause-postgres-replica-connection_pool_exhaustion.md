---
doc_id: runbook-cascade-root-cause-postgres-replica-connection_pool_exhaustion
doc_type: runbook
title: 'postgres-replica: requests stalling while waiting on a database connection
  (cascading)'
services:
- postgres-replica
metadata:
  root_cause_category: connection_pool_exhaustion
---

postgres-replica is showing requests stalling while waiting on a database connection. Because so many services depend on postgres-replica directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single postgres-replica alert -- treat a burst of simultaneous cross-service errors as one postgres-replica incident, not several.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: resolve the condition on postgres-replica directly; the downstream services will recover on their own once it does.
