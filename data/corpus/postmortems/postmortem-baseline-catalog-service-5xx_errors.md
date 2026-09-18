---
doc_id: postmortem-baseline-catalog-service-5xx_errors
doc_type: postmortem
title: 'Postmortem: catalog-service 5xx errors'
services:
- catalog-service
metadata:
  root_cause_service: catalog-service
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: catalog-service experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for catalog-service rather than relying on downstream symptoms to surface it.
