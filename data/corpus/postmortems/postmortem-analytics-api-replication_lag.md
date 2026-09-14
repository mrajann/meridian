---
doc_id: postmortem-analytics-api-replication_lag
doc_type: postmortem
title: 'Postmortem: analytics-api replication lag'
services:
- analytics-api
metadata:
  root_cause_service: analytics-api
  root_cause_category: replication_lag
  affected_services: []
  fragile_service: null
---

Summary: analytics-api experienced reads returning stale or out-of-date data.

Root cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Action items: add direct alerting on this failure mode for analytics-api rather than relying on downstream symptoms to surface it.
