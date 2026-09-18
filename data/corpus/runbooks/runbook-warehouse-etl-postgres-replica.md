---
doc_id: runbook-warehouse-etl-postgres-replica
doc_type: runbook
title: 'warehouse-etl: writes being refused or new work no longer being accepted (postgres-replica
  root cause)'
services:
- warehouse-etl
metadata:
  root_cause_category: disk_full__postgres-replica
---

warehouse-etl is showing writes being refused or new work no longer being accepted. Check the warehouse-etl dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-replica is degraded or unavailable, so warehouse-etl's calls to it are failing or timing out.

Fix: check postgres-replica health directly before touching warehouse-etl itself.
