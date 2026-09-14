---
doc_id: postmortem-chatbot-orchestrator-quality_degradation
doc_type: postmortem
title: 'Postmortem: chatbot-orchestrator quality degradation'
services:
- chatbot-orchestrator
metadata:
  root_cause_service: chatbot-orchestrator
  root_cause_category: quality_degradation
  affected_services: []
  fragile_service: null
---

Summary: chatbot-orchestrator experienced output quality dropping with no traditional error signal.

Root cause: a routing or model-version change degraded output quality without tripping a health check.

Action items: add direct alerting on this failure mode for chatbot-orchestrator rather than relying on downstream symptoms to surface it.
