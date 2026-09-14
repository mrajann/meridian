---
doc_id: postmortem-cdn-config-5xx_errors
doc_type: postmortem
title: 'Postmortem: cdn-config 5xx errors'
services:
- cdn-config
metadata:
  root_cause_service: cdn-config
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: cdn-config experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for cdn-config rather than relying on downstream symptoms to surface it.
