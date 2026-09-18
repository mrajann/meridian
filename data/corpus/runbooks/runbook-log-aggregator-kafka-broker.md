---
doc_id: runbook-log-aggregator-kafka-broker
doc_type: runbook
title: 'log-aggregator: a batch or background job no longer producing fresh output
  (kafka-broker root cause)'
services:
- log-aggregator
metadata:
  root_cause_category: job_failure__kafka-broker
---

log-aggregator is showing a batch or background job no longer producing fresh output. Check the log-aggregator dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: kafka-broker is degraded or unavailable, so log-aggregator's calls to it are failing or timing out.

Fix: check kafka-broker health directly before touching log-aggregator itself.
