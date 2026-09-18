---
doc_id: runbook-cascade-root-cause-postgres-primary-connection_pool_exhaustion
doc_type: runbook
title: 'postgres-primary: requests stalling while waiting on a database connection
  (cascading)'
services:
- postgres-primary
metadata:
  root_cause_category: connection_pool_exhaustion
---

postgres-primary is showing requests stalling while waiting on a database connection. Because so many services depend on postgres-primary directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single postgres-primary alert -- treat a burst of simultaneous cross-service errors as one postgres-primary incident, not several.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: resolve the condition on postgres-primary directly; the downstream services will recover on their own once it does.
