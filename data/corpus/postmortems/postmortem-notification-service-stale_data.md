---
doc_id: postmortem-notification-service-stale_data
doc_type: postmortem
title: 'Postmortem: notification-service stale data'
services:
- notification-service
metadata:
  root_cause_service: notification-service
  root_cause_category: stale_data
  affected_services: []
  fragile_service: notification-service
---

Summary: notification-service experienced results or dashboards reflecting outdated state with no errors thrown.

Root cause: a background refresh or index job has been failing silently.

Action items: add direct alerting on this failure mode for notification-service rather than relying on downstream symptoms to surface it.
