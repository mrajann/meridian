---
doc_id: postmortem-baseline-analytics-api-disk_full
doc_type: postmortem
title: 'Postmortem: analytics-api disk full'
services:
- analytics-api
metadata:
  root_cause_service: analytics-api
  root_cause_category: disk_full
  affected_services: []
  fragile_service: null
---

Summary: analytics-api experienced writes being refused or new work no longer being accepted.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Action items: add direct alerting on this failure mode for analytics-api rather than relying on downstream symptoms to surface it.
