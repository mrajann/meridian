---
doc_id: postmortem-baseline-pricing-engine-5xx_errors
doc_type: postmortem
title: 'Postmortem: pricing-engine 5xx errors'
services:
- pricing-engine
metadata:
  root_cause_service: pricing-engine
  root_cause_category: 5xx_errors
  affected_services: []
  fragile_service: null
---

Summary: pricing-engine experienced an elevated 5xx error rate.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Action items: add direct alerting on this failure mode for pricing-engine rather than relying on downstream symptoms to surface it.
