---
doc_id: catalog-entry-feature-flags
doc_type: catalog_entry
title: 'Service catalog: feature-flags'
services:
- feature-flags
metadata:
  tier: 2
  owner: platform-infra
---

Feature flag evaluation service used for gradual rollouts and kill switches.

Owner: platform-infra. Tier: 2.
Depends on: redis-cache.
Depended on by: api-gateway, llm-gateway.
Availability target: 99.9%.
Blast radius: Flag evaluations fall back to defaults; rollouts and kill switches stop working.
