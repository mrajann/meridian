---
doc_id: postmortem-sendgrid-email-third_party_outage
doc_type: postmortem
title: 'Postmortem: sendgrid-email third party outage'
services:
- sendgrid-email
metadata:
  root_cause_service: sendgrid-email
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: null
---

Summary: sendgrid-email experienced requests to an external provider failing or timing out.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for sendgrid-email rather than relying on downstream symptoms to surface it.
