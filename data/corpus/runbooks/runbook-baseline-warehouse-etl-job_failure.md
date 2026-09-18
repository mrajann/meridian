---
doc_id: runbook-baseline-warehouse-etl-job_failure
doc_type: runbook
title: 'warehouse-etl: job failure'
services:
- warehouse-etl
metadata:
  root_cause_category: job_failure
---

warehouse-etl is showing a batch or background job no longer producing fresh output. Check postgres-replica first -- warehouse-etl depends on it directly. Check the warehouse-etl dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-etl itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-etl -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Analytics and reporting data goes stale. No customer-facing impact.
