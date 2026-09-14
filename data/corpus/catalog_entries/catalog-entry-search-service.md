---
doc_id: catalog-entry-search-service
doc_type: catalog_entry
title: 'Service catalog: search-service'
services:
- search-service
metadata:
  tier: 2
  owner: growth-platform
---

Full-text and faceted product search.

Owner: growth-platform. Tier: 2.
Depends on: postgres-replica, redis-cache.
Depended on by: catalog-service, mobile-api, web-frontend.
Availability target: 99.5%.
Blast radius: Search returns no or stale results. Browsing by category still works.
