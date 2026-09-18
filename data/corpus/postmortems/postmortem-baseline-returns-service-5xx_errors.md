---
doc_id: postmortem-baseline-returns-service-5xx_errors
doc_type: postmortem
title: 'Postmortem: returns-service 5xx errors'
services:
- returns-service
metadata:
  root_cause_service: returns-service
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: returns-service experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for returns-service rather than relying on downstream symptoms to surface it.
