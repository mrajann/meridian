---
doc_id: catalog-entry-checkout-api
doc_type: catalog_entry
title: 'Service catalog: checkout-api'
services:
- checkout-api
metadata:
  tier: 1
  owner: payments-platform
---

Order placement and payment capture. Revenue-critical path.

Owner: payments-platform. Tier: 1.
Depends on: auth-service, postgres-primary, stripe-gateway, inventory-service, pricing-engine.
Depended on by: mobile-api, web-frontend.
Availability target: 99.95%.
Blast radius: All revenue. Complete outage means no orders can be placed.
