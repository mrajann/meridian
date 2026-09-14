---
doc_id: postmortem-stripe-gateway-third_party_outage
doc_type: postmortem
title: 'Postmortem: stripe-gateway third party outage'
services:
- stripe-gateway
metadata:
  root_cause_service: stripe-gateway
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: null
---

Summary: stripe-gateway experienced requests to an external provider failing or timing out.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for stripe-gateway rather than relying on downstream symptoms to surface it.
