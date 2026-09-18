---
doc_id: catalog-entry-config-service
doc_type: catalog_entry
title: 'Service catalog: config-service'
services:
- config-service
metadata:
  tier: 2
  owner: platform-infra
---

Centralized runtime configuration store for all services.

Owner: platform-infra. Tier: 2.
Depends on: postgres-primary.
Depended on by: ci-pipeline.
Availability target: 99.9%.
Blast radius: Services fall back to cached/default config; new config changes don't apply.
