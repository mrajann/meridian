---
doc_id: runbook-auth-service-5xx_errors-postgres-primary
doc_type: runbook
title: 'auth-service: 5xx errors (postgres-primary root cause)'
services:
- auth-service
metadata:
  root_cause_category: 5xx_errors__postgres-primary
---

auth-service is showing an elevated 5xx error rate. Check the auth-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is slow or unavailable, so credential lookups are timing out.

Fix: check postgres-primary health directly before touching auth-service itself.
