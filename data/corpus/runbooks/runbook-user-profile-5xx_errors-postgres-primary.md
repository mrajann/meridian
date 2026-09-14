---
doc_id: runbook-user-profile-5xx_errors-postgres-primary
doc_type: runbook
title: 'user-profile: 5xx errors (postgres-primary root cause)'
services:
- user-profile
metadata:
  root_cause_category: 5xx_errors__postgres-primary
---

user-profile is showing an elevated 5xx error rate. Check the user-profile dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is slow, so profile reads are timing out.

Fix: check postgres-primary health directly.
