---
doc_id: postmortem-postgres-primary-replication_lag-2
doc_type: postmortem
title: 'Postmortem: postgres-primary replication lag (incident #2)'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: replication_lag
  affected_services: []
  fragile_service: postgres-primary
---

Summary: postgres-primary experienced reads returning stale or out-of-date data. This is recorded incident #2 of this type for postgres-primary.

Root cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
