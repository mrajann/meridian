---
doc_id: postmortem-baseline-recommendation-engine-third_party_outage
doc_type: postmortem
title: 'Postmortem: recommendation-engine third party outage'
services:
- recommendation-engine
metadata:
  root_cause_service: recommendation-engine
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: null
---

Summary: recommendation-engine experienced requests to an external provider failing or timing out.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for recommendation-engine rather than relying on downstream symptoms to surface it.
