---
doc_id: postmortem-web-frontend-5xx_errors
doc_type: postmortem
title: 'Postmortem: web-frontend 5xx errors'
services:
- web-frontend
metadata:
  root_cause_service: web-frontend
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: web-frontend experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for web-frontend rather than relying on downstream symptoms to surface it.
