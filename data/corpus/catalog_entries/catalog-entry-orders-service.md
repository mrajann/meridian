---
doc_id: catalog-entry-orders-service
doc_type: catalog_entry
title: 'Service catalog: orders-service'
services:
- orders-service
metadata:
  tier: 1
  owner: commerce-platform
---

Order lifecycle management: creation, status transitions, cancellations.

Owner: commerce-platform. Tier: 1.
Depends on: postgres-primary, inventory-service, pricing-engine, notification-service.
Depended on by: returns-service, shipping-service.
Availability target: 99.9%.
Blast radius: Orders can be placed but status updates and cancellations fail.
