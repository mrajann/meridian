---
doc_id: postmortem-llm-gateway-rate_limit_exhaustion
doc_type: postmortem
title: 'Postmortem: llm-gateway rate limit exhaustion'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: rate_limit_exhaustion
  affected_services: []
  fragile_service: llm-gateway
---

Summary: llm-gateway experienced requests queueing or being rejected outright.

Root cause: aggregate request volume exceeded the provider's quota.

Action items: add direct alerting on this failure mode for llm-gateway rather than relying on downstream symptoms to surface it.
