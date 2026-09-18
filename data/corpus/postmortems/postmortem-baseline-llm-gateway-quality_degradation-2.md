---
doc_id: postmortem-baseline-llm-gateway-quality_degradation-2
doc_type: postmortem
title: 'Postmortem: llm-gateway quality degradation (incident #2)'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: quality_degradation
  affected_services: []
  fragile_service: llm-gateway
---

Summary: llm-gateway experienced output quality dropping with no traditional error signal. This is recorded incident #2 of this type for llm-gateway.

Root cause: a routing or model-version change degraded output quality without tripping a health check.

Action items: add direct alerting on this failure mode for llm-gateway rather than relying on downstream symptoms to surface it.
