---
doc_id: runbook-kafka-broker-replication_lag
doc_type: runbook
title: 'kafka-broker: replication lag'
services:
- kafka-broker
metadata:
  root_cause_category: replication_lag
---

kafka-broker is showing reads returning stale or out-of-date data. Check the kafka-broker dashboard and recent deploys via ci-pipeline before assuming the fault is in kafka-broker itself.

Likely cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting kafka-broker -- a restart will not fix replication lag if the underlying condition is still present.

Blast radius: Async notifications and metrics/log pipelines fall behind or stop.
