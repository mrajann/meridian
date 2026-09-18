---
doc_id: postmortem-baseline-warehouse-etl-disk_full
doc_type: postmortem
title: 'Postmortem: warehouse-etl disk full'
services:
- warehouse-etl
metadata:
  root_cause_service: warehouse-etl
  root_cause_category: disk_full
  affected_services: []
  fragile_service: null
---

Summary: warehouse-etl experienced writes being refused or new work no longer being accepted.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Action items: add direct alerting on this failure mode for warehouse-etl rather than relying on downstream symptoms to surface it.
