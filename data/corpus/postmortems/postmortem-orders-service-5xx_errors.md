---
doc_id: postmortem-orders-service-5xx_errors
doc_type: postmortem
title: 'Postmortem: orders-service 5xx errors'
services:
- orders-service
metadata:
  root_cause_service: orders-service
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: orders-service experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for orders-service rather than relying on downstream symptoms to surface it.
