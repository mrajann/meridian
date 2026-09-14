---
doc_id: catalog-entry-postgres-primary
doc_type: catalog_entry
title: 'Service catalog: postgres-primary'
services:
- postgres-primary
metadata:
  tier: 1
  owner: data-platform
---

Primary relational datastore for orders, inventory, pricing, and auth.

Owner: data-platform. Tier: 1.
Depends on: nothing.
Depended on by: auth-service, catalog-service, checkout-api, config-service, inventory-service, orders-service, postgres-replica, pricing-engine, returns-service, shipping-service, user-profile, warehouse-api.
Availability target: 99.99%.
Blast radius: All revenue. Nearly every core-business and platform service reads or writes here.
