---
doc_id: postmortem-kafka-broker-disk_full
doc_type: postmortem
title: 'Postmortem: kafka-broker disk full'
services:
- kafka-broker
metadata:
  root_cause_service: kafka-broker
  root_cause_category: disk_full
  affected_services: []
  fragile_service: null
---

Summary: kafka-broker experienced writes being refused or new work no longer being accepted.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Action items: add direct alerting on this failure mode for kafka-broker rather than relying on downstream symptoms to surface it.
