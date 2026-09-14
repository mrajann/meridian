---
doc_id: runbook-auth-service-connection_pool_exhaustion
doc_type: runbook
title: 'auth-service: connection pool exhaustion'
services:
- auth-service
metadata:
  root_cause_category: connection_pool_exhaustion
---

auth-service is showing requests stalling while waiting on a database connection. Check postgres-primary first -- auth-service depends on it directly. Check the auth-service dashboard and recent deploys via ci-pipeline before assuming the fault is in auth-service itself.

Likely cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting auth-service -- a restart will not fix connection pool exhaustion if the underlying condition is still present.

Blast radius: No one can log in. Cascades to every service behind api-gateway.
