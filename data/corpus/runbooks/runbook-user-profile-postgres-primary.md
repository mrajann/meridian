---
doc_id: runbook-user-profile-postgres-primary
doc_type: runbook
title: 'user-profile: requests stalling while waiting on a database connection (postgres-primary
  root cause)'
services:
- user-profile
metadata:
  root_cause_category: connection_pool_exhaustion__postgres-primary
---

user-profile is showing requests stalling while waiting on a database connection. Check the user-profile dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is degraded or unavailable, so user-profile's calls to it are failing or timing out.

Fix: check postgres-primary health directly before touching user-profile itself.
