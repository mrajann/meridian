---
doc_id: postmortem-baseline-llm-gateway-upstream_timeout
doc_type: postmortem
title: 'Postmortem: llm-gateway upstream timeout'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: upstream_timeout
  affected_services: []
  fragile_service: llm-gateway
---

Summary: llm-gateway experienced elevated latency or errors tracing to one specific upstream call.

Root cause: a synchronous call to a slow or degraded upstream is blocking the request path.

Action items: add direct alerting on this failure mode for llm-gateway rather than relying on downstream symptoms to surface it.
