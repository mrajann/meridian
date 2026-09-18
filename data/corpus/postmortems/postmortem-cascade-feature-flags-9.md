---
doc_id: postmortem-cascade-feature-flags-9
doc_type: postmortem
title: 'Postmortem: feature-flags cascade (unexpected behavior with no code change
  involved)'
services:
- feature-flags
- api-gateway
- chatbot-orchestrator
- llm-gateway
- mobile-api
- rag-retriever
- recommendation-engine
metadata:
  root_cause_service: feature-flags
  root_cause_category: misconfiguration
  affected_services:
  - api-gateway
  - chatbot-orchestrator
  - llm-gateway
  - mobile-api
  - rag-retriever
  - recommendation-engine
  fragile_service: null
  adversarial_case: cascading_failure
---

Summary: feature-flags experienced unexpected behavior with no code change involved. This produced symptoms in 6 dependent services at once: api-gateway, chatbot-orchestrator, llm-gateway, mobile-api, rag-retriever, recommendation-engine.

Root cause: a configuration change had a broader blast radius than intended.

On-call for several of the affected services were paged independently before the shared root cause on feature-flags was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on feature-flags rather than relying on downstream symptoms to surface a shared root cause.
