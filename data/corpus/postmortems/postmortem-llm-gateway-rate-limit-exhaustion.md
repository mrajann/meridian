---
doc_id: postmortem-llm-gateway-rate-limit-exhaustion
doc_type: postmortem
title: 'Postmortem: llm-gateway rate limit exhaustion'
services:
- llm-gateway
- chatbot-orchestrator
- voicebot-asr
- recommendation-engine
metadata:
  root_cause_service: llm-gateway
  root_cause_category: rate_limit_exhaustion
  affected_services:
  - chatbot-orchestrator
  - voicebot-asr
  - recommendation-engine
  fragile_service: llm-gateway
---

Summary: a marketing push drove a 3x spike in recommendation-engine traffic, which consumed enough of llm-gateway's shared provider quota that chatbot-orchestrator and voicebot-asr both began queuing and timing out.

Root cause: llm-gateway has no per-consumer rate limiting of its own -- it passes the provider's aggregate rate limit straight through, so one noisy consumer can starve the others.

Action items: add per-consumer quotas inside llm-gateway so a traffic spike in one AI-layer service cannot degrade the others.
