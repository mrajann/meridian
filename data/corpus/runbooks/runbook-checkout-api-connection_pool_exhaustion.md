---
doc_id: runbook-checkout-api-connection_pool_exhaustion
doc_type: runbook
title: 'checkout-api: connection pool exhaustion'
services:
- checkout-api
metadata:
  root_cause_category: connection_pool_exhaustion
---

checkout-api is showing requests stalling while waiting on a database connection. Check auth-service first -- checkout-api depends on it directly. Check the checkout-api dashboard and recent deploys via ci-pipeline before assuming the fault is in checkout-api itself.

Likely cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting checkout-api -- a restart will not fix connection pool exhaustion if the underlying condition is still present.

Blast radius: All revenue. Complete outage means no orders can be placed.
