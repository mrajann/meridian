---
doc_id: catalog-entry-api-gateway
doc_type: catalog_entry
title: 'Service catalog: api-gateway'
services:
- api-gateway
metadata:
  tier: 1
  owner: edge-platform
---

Ingress point for all external API traffic; auth enforcement, routing, rate limiting.

Owner: edge-platform. Tier: 1.
Depends on: auth-service, feature-flags.
Depended on by: mobile-api, web-frontend.
Availability target: 99.95%.
Blast radius: All web and mobile traffic blocked. Complete customer-facing outage.
