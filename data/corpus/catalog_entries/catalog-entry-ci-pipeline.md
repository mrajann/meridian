---
doc_id: catalog-entry-ci-pipeline
doc_type: catalog_entry
title: 'Service catalog: ci-pipeline'
services:
- ci-pipeline
metadata:
  tier: 3
  owner: platform-infra
---

Build, test, and deploy pipeline for all Meridian services.

Owner: platform-infra. Tier: 3.
Depends on: secrets-manager, config-service.
Depended on by: nothing.
Availability target: 99.0%.
Blast radius: Deploys are blocked. No impact to already-running services.
