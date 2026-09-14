---
doc_id: catalog-entry-warehouse-etl
doc_type: catalog_entry
title: 'Service catalog: warehouse-etl'
services:
- warehouse-etl
metadata:
  tier: 2
  owner: data-platform
---

Nightly batch jobs replicating operational data into the analytics warehouse.

Owner: data-platform. Tier: 2.
Depends on: postgres-replica, s3-storage.
Depended on by: analytics-api.
Availability target: 99.0%.
Blast radius: Analytics and reporting data goes stale. No customer-facing impact.
