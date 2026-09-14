---
doc_id: postmortem-cloudflare-cdn-third_party_outage
doc_type: postmortem
title: 'Postmortem: cloudflare-cdn third party outage'
services:
- cloudflare-cdn
metadata:
  root_cause_service: cloudflare-cdn
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: null
---

Summary: cloudflare-cdn experienced requests to an external provider failing or timing out.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for cloudflare-cdn rather than relying on downstream symptoms to surface it.
