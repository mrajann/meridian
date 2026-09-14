---
doc_id: runbook-postgres-primary-connection_pool_exhaustion
doc_type: runbook
title: 'postgres-primary: connection pool exhaustion'
services:
- postgres-primary
metadata:
  root_cause_category: connection_pool_exhaustion
---

postgres-primary is showing requests stalling while waiting on a database connection. Check the postgres-primary dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-primary itself.

Likely cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-primary -- a restart will not fix connection pool exhaustion if the underlying condition is still present.

Blast radius: All revenue. Nearly every core-business and platform service reads or writes here.
