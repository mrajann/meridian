---
doc_id: catalog-entry-catalog-service
doc_type: catalog_entry
title: 'Service catalog: catalog-service'
services:
- catalog-service
metadata:
  tier: 1
  owner: commerce-platform
---

Product catalog: listings, categories, and product metadata.

Owner: commerce-platform. Tier: 1.
Depends on: postgres-primary, redis-cache, search-service.
Depended on by: web-frontend.
Availability target: 99.9%.
Blast radius: Product pages fail to load or show missing/stale data.
