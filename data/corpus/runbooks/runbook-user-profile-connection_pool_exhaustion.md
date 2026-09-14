---
doc_id: runbook-user-profile-connection_pool_exhaustion
doc_type: runbook
title: 'user-profile: connection pool exhaustion'
services:
- user-profile
metadata:
  root_cause_category: connection_pool_exhaustion
---

user-profile is showing requests stalling while waiting on a database connection. Check postgres-primary first -- user-profile depends on it directly. Check the user-profile dashboard and recent deploys via ci-pipeline before assuming the fault is in user-profile itself.

Likely cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting user-profile -- a restart will not fix connection pool exhaustion if the underlying condition is still present.

Blast radius: Customers cannot view or edit profile/address data.
