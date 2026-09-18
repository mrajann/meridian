---
doc_id: runbook-baseline-kafka-broker-job_failure
doc_type: runbook
title: 'kafka-broker: job failure'
services:
- kafka-broker
metadata:
  root_cause_category: job_failure
---

kafka-broker is showing a batch or background job no longer producing fresh output. Check the kafka-broker dashboard and recent deploys via ci-pipeline before assuming the fault is in kafka-broker itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting kafka-broker -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Async notifications and metrics/log pipelines fall behind or stop.
