---
doc_id: catalog-entry-inventory-service
doc_type: catalog_entry
title: 'Service catalog: inventory-service'
services:
- inventory-service
metadata:
  tier: 1
  owner: commerce-platform
---

Tracks stock levels and reservations across warehouses.

Owner: commerce-platform. Tier: 1.
Depends on: postgres-primary, redis-cache.
Depended on by: cart-service, checkout-api, orders-service, warehouse-api.
Availability target: 99.9%.
Blast radius: Risk of overselling out-of-stock items; checkout may show stale availability.
