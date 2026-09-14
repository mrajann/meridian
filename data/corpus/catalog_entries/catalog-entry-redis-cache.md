---
doc_id: catalog-entry-redis-cache
doc_type: catalog_entry
title: 'Service catalog: redis-cache'
services:
- redis-cache
metadata:
  tier: 1
  owner: data-platform
---

Shared in-memory cache for sessions, pricing, and cart state.

Owner: data-platform. Tier: 1.
Depends on: nothing.
Depended on by: auth-service, cart-service, catalog-service, feature-flags, inventory-service, pricing-engine, recommendation-engine, search-service, session-store.
Availability target: 99.95%.
Blast radius: Elevated latency and error rates across most core-business services.
