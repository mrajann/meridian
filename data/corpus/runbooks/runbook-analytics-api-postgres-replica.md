---
doc_id: runbook-analytics-api-postgres-replica
doc_type: runbook
title: 'analytics-api: writes being refused or new work no longer being accepted (postgres-replica
  root cause)'
services:
- analytics-api
metadata:
  root_cause_category: disk_full__postgres-replica
---

analytics-api is showing writes being refused or new work no longer being accepted. Check the analytics-api dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-replica is degraded or unavailable, so analytics-api's calls to it are failing or timing out.

Fix: check postgres-replica health directly before touching analytics-api itself.
