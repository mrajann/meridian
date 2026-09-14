---
doc_id: postmortem-auth-service-cache_eviction
doc_type: postmortem
title: 'Postmortem: auth-service cache eviction'
services:
- auth-service
metadata:
  root_cause_service: auth-service
  root_cause_category: cache_eviction
  affected_services: []
  fragile_service: null
---

Summary: auth-service experienced elevated latency and a rise in cold-cache misses.

Root cause: an eviction policy or memory limit change is evicting entries faster than expected.

Action items: add direct alerting on this failure mode for auth-service rather than relying on downstream symptoms to surface it.
