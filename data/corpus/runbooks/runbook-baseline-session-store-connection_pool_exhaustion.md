---
doc_id: runbook-baseline-session-store-connection_pool_exhaustion
doc_type: runbook
title: 'session-store: connection pool exhaustion'
services:
- session-store
metadata:
  root_cause_category: connection_pool_exhaustion
---

session-store is showing requests stalling while waiting on a database connection. Check redis-cache first -- session-store depends on it directly. Check the session-store dashboard and recent deploys via ci-pipeline before assuming the fault is in session-store itself.

Likely cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting session-store -- a restart will not fix connection pool exhaustion if the underlying condition is still present.

Blast radius: Users get logged out unexpectedly; new logins may fail.
