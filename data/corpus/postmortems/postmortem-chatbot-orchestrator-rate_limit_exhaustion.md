---
doc_id: postmortem-chatbot-orchestrator-rate_limit_exhaustion
doc_type: postmortem
title: 'Postmortem: chatbot-orchestrator rate limit exhaustion'
services:
- chatbot-orchestrator
metadata:
  root_cause_service: chatbot-orchestrator
  root_cause_category: rate_limit_exhaustion
  affected_services: []
  fragile_service: null
---

Summary: chatbot-orchestrator experienced requests queueing or being rejected outright.

Root cause: aggregate request volume exceeded the provider's quota.

Action items: add direct alerting on this failure mode for chatbot-orchestrator rather than relying on downstream symptoms to surface it.
