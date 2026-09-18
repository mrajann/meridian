---
doc_id: postmortem-baseline-llm-gateway-latency_spike-4
doc_type: postmortem
title: 'Postmortem: llm-gateway latency spike (incident #4)'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: latency_spike
  affected_services: []
  fragile_service: llm-gateway
---

Summary: llm-gateway experienced p99 latency above its SLO target. This is recorded incident #4 of this type for llm-gateway.

Root cause: a slow query or an undersized resource pool is queueing requests.

Action items: add direct alerting on this failure mode for llm-gateway rather than relying on downstream symptoms to surface it.
