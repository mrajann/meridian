---
doc_id: runbook-llm-gateway-quality_degradation
doc_type: runbook
title: 'llm-gateway: quality degradation'
services:
- llm-gateway
metadata:
  root_cause_category: quality_degradation
---

llm-gateway is showing output quality dropping with no traditional error signal. Check secrets-manager first -- llm-gateway depends on it directly. Check the llm-gateway dashboard and recent deploys via ci-pipeline before assuming the fault is in llm-gateway itself.

Likely cause: a routing or model-version change degraded output quality without tripping a health check.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting llm-gateway -- a restart will not fix quality degradation if the underlying condition is still present.

Blast radius: All AI-layer features (chatbot, voicebot, recommendations, RAG) degrade or fail.
