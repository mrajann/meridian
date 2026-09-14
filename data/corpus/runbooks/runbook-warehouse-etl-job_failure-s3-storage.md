---
doc_id: runbook-warehouse-etl-job_failure-s3-storage
doc_type: runbook
title: 'warehouse-etl: job failure (s3-storage root cause)'
services:
- warehouse-etl
metadata:
  root_cause_category: job_failure__s3-storage
---

warehouse-etl is showing a batch or background job no longer producing fresh output. Check the warehouse-etl dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: s3-storage rejected writes during the job's load phase.

Fix: check s3-storage access and quota, then rerun the job from the load phase.
