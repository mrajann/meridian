---
doc_id: catalog-entry-kafka-broker
doc_type: catalog_entry
title: 'Service catalog: kafka-broker'
services:
- kafka-broker
metadata:
  tier: 2
  owner: data-platform
---

Event bus for async workflows: notifications, analytics, log shipping.

Owner: data-platform. Tier: 2.
Depends on: nothing.
Depended on by: log-aggregator, metrics-collector, notification-service.
Availability target: 99.9%.
Blast radius: Async notifications and metrics/log pipelines fall behind or stop.
