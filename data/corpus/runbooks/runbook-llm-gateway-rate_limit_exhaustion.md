---
doc_id: runbook-llm-gateway-rate_limit_exhaustion
doc_type: runbook
title: 'llm-gateway: rate limit exhaustion'
services:
- llm-gateway
metadata:
  root_cause_category: rate_limit_exhaustion
---

llm-gateway is showing requests queueing or being rejected outright. Check secrets-manager first -- llm-gateway depends on it directly. Check the llm-gateway dashboard and recent deploys via ci-pipeline before assuming the fault is in llm-gateway itself.

Likely cause: aggregate request volume exceeded the provider's quota.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting llm-gateway -- a restart will not fix rate limit exhaustion if the underlying condition is still present.

Blast radius: All AI-layer features (chatbot, voicebot, recommendations, RAG) degrade or fail.
