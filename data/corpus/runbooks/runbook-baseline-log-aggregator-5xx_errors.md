---
doc_id: runbook-baseline-log-aggregator-5xx_errors
doc_type: runbook
title: 'log-aggregator: 5xx errors'
services:
- log-aggregator
metadata:
  root_cause_category: 5xx_errors
---

log-aggregator is showing an elevated 5xx error rate. Check kafka-broker first -- log-aggregator depends on it directly. Check the log-aggregator dashboard and recent deploys via ci-pipeline before assuming the fault is in log-aggregator itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting log-aggregator -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Logs delayed or missing. No impact to serving traffic; hurts debugging.
