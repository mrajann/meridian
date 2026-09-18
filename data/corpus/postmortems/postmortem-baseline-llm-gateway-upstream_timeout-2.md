---
doc_id: postmortem-baseline-llm-gateway-upstream_timeout-2
doc_type: postmortem
title: 'Postmortem: llm-gateway upstream timeout (incident #2)'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: upstream_timeout
  affected_services: []
  fragile_service: llm-gateway
---

Summary: llm-gateway experienced elevated latency or errors tracing to one specific upstream call. This is recorded incident #2 of this type for llm-gateway.

Root cause: a synchronous call to a slow or degraded upstream is blocking the request path.

Action items: add direct alerting on this failure mode for llm-gateway rather than relying on downstream symptoms to surface it.
