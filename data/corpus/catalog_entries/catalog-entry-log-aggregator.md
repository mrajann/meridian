---
doc_id: catalog-entry-log-aggregator
doc_type: catalog_entry
title: 'Service catalog: log-aggregator'
services:
- log-aggregator
metadata:
  tier: 3
  owner: platform-infra
---

Centralized log collection and indexing for all services.

Owner: platform-infra. Tier: 3.
Depends on: kafka-broker, s3-storage.
Depended on by: nothing.
Availability target: 99.0%.
Blast radius: Logs delayed or missing. No impact to serving traffic; hurts debugging.
