---
doc_id: postmortem-baseline-llm-gateway-rate_limit_exhaustion-5
doc_type: postmortem
title: 'Postmortem: llm-gateway rate limit exhaustion (incident #5)'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: rate_limit_exhaustion
  affected_services: []
  fragile_service: llm-gateway
---

Summary: llm-gateway experienced requests queueing or being rejected outright. This is recorded incident #5 of this type for llm-gateway.

Root cause: aggregate request volume exceeded the provider's quota.

Action items: add direct alerting on this failure mode for llm-gateway rather than relying on downstream symptoms to surface it.
