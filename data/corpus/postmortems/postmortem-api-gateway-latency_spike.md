---
doc_id: postmortem-api-gateway-latency_spike
doc_type: postmortem
title: 'Postmortem: api-gateway latency spike'
services:
- api-gateway
metadata:
  root_cause_service: api-gateway
  root_cause_category: latency_spike
  affected_services: []
  fragile_service: null
---

Summary: api-gateway experienced p99 latency above its SLO target.

Root cause: a slow query or an undersized resource pool is queueing requests.

Action items: add direct alerting on this failure mode for api-gateway rather than relying on downstream symptoms to surface it.
