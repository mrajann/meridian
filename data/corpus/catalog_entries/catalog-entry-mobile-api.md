---
doc_id: catalog-entry-mobile-api
doc_type: catalog_entry
title: 'Service catalog: mobile-api'
services:
- mobile-api
metadata:
  tier: 1
  owner: edge-platform
---

Backend-for-frontend API consumed by the iOS and Android apps.

Owner: edge-platform. Tier: 1.
Depends on: api-gateway, checkout-api, cart-service, search-service, auth-service.
Depended on by: nothing.
Availability target: 99.9%.
Blast radius: Mobile app customers cannot browse or check out. Web storefront unaffected.
