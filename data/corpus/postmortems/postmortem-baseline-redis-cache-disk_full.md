---
doc_id: postmortem-baseline-redis-cache-disk_full
doc_type: postmortem
title: 'Postmortem: redis-cache disk full'
services:
- redis-cache
metadata:
  root_cause_service: redis-cache
  root_cause_category: disk_full
  affected_services: []
  fragile_service: null
---

Summary: redis-cache experienced writes being refused or new work no longer being accepted.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Action items: add direct alerting on this failure mode for redis-cache rather than relying on downstream symptoms to surface it.
