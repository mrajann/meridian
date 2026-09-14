---
doc_id: postmortem-search-service-third_party_outage
doc_type: postmortem
title: 'Postmortem: search-service third party outage'
services:
- search-service
metadata:
  root_cause_service: search-service
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: null
---

Summary: search-service experienced requests to an external provider failing or timing out.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for search-service rather than relying on downstream symptoms to surface it.
