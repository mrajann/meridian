---
doc_id: postmortem-baseline-mobile-api-5xx_errors
doc_type: postmortem
title: 'Postmortem: mobile-api 5xx errors'
services:
- mobile-api
metadata:
  root_cause_service: mobile-api
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: mobile-api experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for mobile-api rather than relying on downstream symptoms to surface it.
