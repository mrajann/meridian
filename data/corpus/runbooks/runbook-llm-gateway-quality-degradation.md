---
doc_id: runbook-llm-gateway-quality-degradation
doc_type: runbook
title: 'llm-gateway: response quality degradation'
services:
- llm-gateway
- chatbot-orchestrator
metadata:
  root_cause_category: quality_degradation
---

No errors, no elevated latency, no failed requests -- but chatbot-orchestrator's responses are getting worse, or customer complaints about the chatbot are rising. This is llm-gateway's most distinctive failure mode: the underlying model or a routing change degrades output quality without tripping any traditional health check.

Fix: check llm-gateway's model-version routing config for a recent change (provider-side model deprecation, a new default model, or a feature-flag rollout). Roll back the routing config first and confirm quality recovers before investigating further -- do not assume this is a rag-retriever grounding problem until llm-gateway's own routing has been ruled out.
