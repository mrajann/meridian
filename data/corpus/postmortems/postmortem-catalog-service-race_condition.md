---
doc_id: postmortem-catalog-service-race_condition
doc_type: postmortem
title: 'Postmortem: catalog-service race condition'
services:
- catalog-service
metadata:
  root_cause_service: catalog-service
  root_cause_category: race_condition
  affected_services: []
  fragile_service: null
---

Summary: catalog-service experienced inconsistent or duplicated state under concurrent load.

Root cause: two concurrent operations both read stale state before either write committed.

Action items: add direct alerting on this failure mode for catalog-service rather than relying on downstream symptoms to surface it.
