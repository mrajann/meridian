---
doc_id: catalog-entry-cart-service
doc_type: catalog_entry
title: 'Service catalog: cart-service'
services:
- cart-service
metadata:
  tier: 1
  owner: commerce-platform
---

Shopping cart state: line items, quantities, applied promotions.

Owner: commerce-platform. Tier: 1.
Depends on: redis-cache, pricing-engine, inventory-service.
Depended on by: mobile-api, web-frontend.
Availability target: 99.9%.
Blast radius: Customers cannot add items to cart or see incorrect cart contents.
