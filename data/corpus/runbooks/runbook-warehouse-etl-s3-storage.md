---
doc_id: runbook-warehouse-etl-s3-storage
doc_type: runbook
title: 'warehouse-etl: writes being refused or new work no longer being accepted (s3-storage
  root cause)'
services:
- warehouse-etl
metadata:
  root_cause_category: disk_full__s3-storage
---

warehouse-etl is showing writes being refused or new work no longer being accepted. Check the warehouse-etl dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: s3-storage is degraded or unavailable, so warehouse-etl's calls to it are failing or timing out.

Fix: check s3-storage health directly before touching warehouse-etl itself.
