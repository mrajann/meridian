---
doc_id: catalog-entry-analytics-api
doc_type: catalog_entry
title: 'Service catalog: analytics-api'
services:
- analytics-api
metadata:
  tier: 2
  owner: data-platform
---

Internal API serving dashboards and reporting off warehouse data.

Owner: data-platform. Tier: 2.
Depends on: warehouse-etl, postgres-replica.
Depended on by: recommendation-engine.
Availability target: 99.0%.
Blast radius: Internal dashboards unavailable or stale. No customer-facing impact.
