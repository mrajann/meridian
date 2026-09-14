---
doc_id: runbook-warehouse-etl-job_failure-postgres-replica
doc_type: runbook
title: 'warehouse-etl: job failure (postgres-replica root cause)'
services:
- warehouse-etl
metadata:
  root_cause_category: job_failure__postgres-replica
---

warehouse-etl is showing a batch or background job no longer producing fresh output. Check the warehouse-etl dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-replica was unreachable during the job's extract phase.

Fix: check postgres-replica availability during the job's scheduled window and rerun.
