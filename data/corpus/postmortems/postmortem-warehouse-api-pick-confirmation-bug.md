---
doc_id: postmortem-warehouse-api-pick-confirmation-bug
doc_type: postmortem
title: 'Postmortem: warehouse-api pick-confirmation schema mismatch'
services:
- warehouse-api
metadata:
  root_cause_service: warehouse-api
  root_cause_category: schema_mismatch
  affected_services: []
  fragile_service: null
---

Summary: a subset of warehouse floor scanners running outdated firmware sent pick confirmations in a schema that a recent warehouse-api deploy no longer accepted, causing intermittent 500s.

Root cause: the deploy assumed all scanners had received a firmware update that was, in practice, only partially rolled out across warehouses.

Action items: version the pick-confirmation endpoint and support the previous schema for one full firmware rollout cycle.
