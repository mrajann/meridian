---
doc_id: runbook-analytics-api-warehouse-etl
doc_type: runbook
title: 'analytics-api: writes being refused or new work no longer being accepted (warehouse-etl
  root cause)'
services:
- analytics-api
metadata:
  root_cause_category: disk_full__warehouse-etl
---

analytics-api is showing writes being refused or new work no longer being accepted. Check the analytics-api dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: warehouse-etl is degraded or unavailable, so analytics-api's calls to it are failing or timing out.

Fix: check warehouse-etl health directly before touching analytics-api itself.
