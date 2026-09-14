---
doc_id: postmortem-notification-service-quality_degradation-2
doc_type: postmortem
title: 'Postmortem: notification-service quality degradation (incident #2)'
services:
- notification-service
metadata:
  root_cause_service: notification-service
  root_cause_category: quality_degradation
  affected_services: []
  fragile_service: notification-service
---

Summary: notification-service experienced output quality dropping with no traditional error signal. This is recorded incident #2 of this type for notification-service.

Root cause: a routing or model-version change degraded output quality without tripping a health check.

Action items: add direct alerting on this failure mode for notification-service rather than relying on downstream symptoms to surface it.
