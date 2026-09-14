---
doc_id: postmortem-shipping-service-5xx_errors
doc_type: postmortem
title: 'Postmortem: shipping-service 5xx errors'
services:
- shipping-service
metadata:
  root_cause_service: shipping-service
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: shipping-service experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for shipping-service rather than relying on downstream symptoms to surface it.
