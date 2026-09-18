---
doc_id: runbook-baseline-kafka-broker-memory_leak
doc_type: runbook
title: 'kafka-broker: memory leak'
services:
- kafka-broker
metadata:
  root_cause_category: memory_leak
---

kafka-broker is showing gradually increasing memory usage and periodic restarts. Check the kafka-broker dashboard and recent deploys via ci-pipeline before assuming the fault is in kafka-broker itself.

Likely cause: a memory leak accumulates until the process is killed for excess memory use and restarts.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting kafka-broker -- a restart will not fix memory leak if the underlying condition is still present.

Blast radius: Async notifications and metrics/log pipelines fall behind or stop.
