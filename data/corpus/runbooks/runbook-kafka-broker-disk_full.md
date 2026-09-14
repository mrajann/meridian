---
doc_id: runbook-kafka-broker-disk_full
doc_type: runbook
title: 'kafka-broker: disk full'
services:
- kafka-broker
metadata:
  root_cause_category: disk_full
---

kafka-broker is showing writes being refused or new work no longer being accepted. Check the kafka-broker dashboard and recent deploys via ci-pipeline before assuming the fault is in kafka-broker itself.

Likely cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting kafka-broker -- a restart will not fix disk full if the underlying condition is still present.

Blast radius: Async notifications and metrics/log pipelines fall behind or stop.
