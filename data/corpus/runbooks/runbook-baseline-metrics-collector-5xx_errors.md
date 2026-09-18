---
doc_id: runbook-baseline-metrics-collector-5xx_errors
doc_type: runbook
title: 'metrics-collector: 5xx errors'
services:
- metrics-collector
metadata:
  root_cause_category: 5xx_errors
---

metrics-collector is showing an elevated 5xx error rate. Check kafka-broker first -- metrics-collector depends on it directly. Check the metrics-collector dashboard and recent deploys via ci-pipeline before assuming the fault is in metrics-collector itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting metrics-collector -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Metrics and alerting degrade; services keep serving traffic normally.
