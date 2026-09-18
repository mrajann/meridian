---
doc_id: postmortem-baseline-postgres-primary-disk_full
doc_type: postmortem
title: 'Postmortem: postgres-primary disk full'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: disk_full
  affected_services: []
  fragile_service: postgres-primary
---

Summary: postgres-primary experienced writes being refused or new work no longer being accepted.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
