---
doc_id: catalog-entry-cdn-config
doc_type: catalog_entry
title: 'Service catalog: cdn-config'
services:
- cdn-config
metadata:
  tier: 1
  owner: edge-platform
---

Manages CDN routing rules, cache invalidation, and edge redirects.

Owner: edge-platform. Tier: 1.
Depends on: cloudflare-cdn.
Depended on by: nothing.
Availability target: 99.9%.
Blast radius: Stale or broken content served at the edge; asset load failures.
