---
doc_id: catalog-entry-metrics-collector
doc_type: catalog_entry
title: 'Service catalog: metrics-collector'
services:
- metrics-collector
metadata:
  tier: 3
  owner: platform-infra
---

Collects and stores service-level metrics backing dashboards and alerts.

Owner: platform-infra. Tier: 3.
Depends on: kafka-broker.
Depended on by: nothing.
Availability target: 99.0%.
Blast radius: Metrics and alerting degrade; services keep serving traffic normally.
