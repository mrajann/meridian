---
doc_id: postmortem-cart-service-race_condition
doc_type: postmortem
title: 'Postmortem: cart-service race condition'
services:
- cart-service
metadata:
  root_cause_service: cart-service
  root_cause_category: race_condition
  affected_services: []
  fragile_service: null
---

Summary: cart-service experienced inconsistent or duplicated state under concurrent load.

Root cause: two concurrent operations both read stale state before either write committed.

Action items: add direct alerting on this failure mode for cart-service rather than relying on downstream symptoms to surface it.
