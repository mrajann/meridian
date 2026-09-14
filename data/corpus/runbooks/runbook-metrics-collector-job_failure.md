---
doc_id: runbook-metrics-collector-job_failure
doc_type: runbook
title: 'metrics-collector: job failure'
services:
- metrics-collector
metadata:
  root_cause_category: job_failure
---

metrics-collector is showing a batch or background job no longer producing fresh output. Check kafka-broker first -- metrics-collector depends on it directly. Check the metrics-collector dashboard and recent deploys via ci-pipeline before assuming the fault is in metrics-collector itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting metrics-collector -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Metrics and alerting degrade; services keep serving traffic normally.
