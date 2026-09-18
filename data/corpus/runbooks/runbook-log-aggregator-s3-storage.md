---
doc_id: runbook-log-aggregator-s3-storage
doc_type: runbook
title: 'log-aggregator: a batch or background job no longer producing fresh output
  (s3-storage root cause)'
services:
- log-aggregator
metadata:
  root_cause_category: job_failure__s3-storage
---

log-aggregator is showing a batch or background job no longer producing fresh output. Check the log-aggregator dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: s3-storage is degraded or unavailable, so log-aggregator's calls to it are failing or timing out.

Fix: check s3-storage health directly before touching log-aggregator itself.
