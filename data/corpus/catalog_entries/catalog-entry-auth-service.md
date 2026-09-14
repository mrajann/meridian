---
doc_id: catalog-entry-auth-service
doc_type: catalog_entry
title: 'Service catalog: auth-service'
services:
- auth-service
metadata:
  tier: 1
  owner: identity-platform
---

Authentication and session token issuance for all customer and internal traffic.

Owner: identity-platform. Tier: 1.
Depends on: postgres-primary, redis-cache, secrets-manager.
Depended on by: api-gateway, checkout-api, mobile-api, web-frontend.
Availability target: 99.95%.
Blast radius: No one can log in. Cascades to every service behind api-gateway.
