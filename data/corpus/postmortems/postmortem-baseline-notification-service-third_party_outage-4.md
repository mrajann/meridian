---
doc_id: postmortem-baseline-notification-service-third_party_outage-4
doc_type: postmortem
title: 'Postmortem: notification-service third party outage (incident #4)'
services:
- notification-service
metadata:
  root_cause_service: notification-service
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: notification-service
---

Summary: notification-service experienced requests to an external provider failing or timing out. This is recorded incident #4 of this type for notification-service.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for notification-service rather than relying on downstream symptoms to surface it.
