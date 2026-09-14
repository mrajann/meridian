---
doc_id: postmortem-notification-service-latency_spike-2
doc_type: postmortem
title: 'Postmortem: notification-service latency spike (incident #2)'
services:
- notification-service
metadata:
  root_cause_service: notification-service
  root_cause_category: latency_spike
  affected_services: []
  fragile_service: notification-service
---

Summary: notification-service experienced p99 latency above its SLO target. This is recorded incident #2 of this type for notification-service.

Root cause: a slow query or an undersized resource pool is queueing requests.

Action items: add direct alerting on this failure mode for notification-service rather than relying on downstream symptoms to surface it.
