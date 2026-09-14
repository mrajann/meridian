---
doc_id: catalog-entry-secrets-manager
doc_type: catalog_entry
title: 'Service catalog: secrets-manager'
services:
- secrets-manager
metadata:
  tier: 2
  owner: platform-infra
---

Stores and rotates API keys, credentials, and certificates.

Owner: platform-infra. Tier: 2.
Depends on: nothing.
Depended on by: auth-service, ci-pipeline, llm-gateway.
Availability target: 99.95%.
Blast radius: Services with expiring credentials begin failing auth to their dependencies.
