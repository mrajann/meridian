---
doc_id: postmortem-cdn-config-latency_spike
doc_type: postmortem
title: 'Postmortem: cdn-config latency spike'
services:
- cdn-config
metadata:
  root_cause_service: cdn-config
  root_cause_category: latency_spike
  affected_services: []
  fragile_service: null
---

Summary: cdn-config experienced p99 latency above its SLO target.

Root cause: a slow query or an undersized resource pool is queueing requests.

Action items: add direct alerting on this failure mode for cdn-config rather than relying on downstream symptoms to surface it.
