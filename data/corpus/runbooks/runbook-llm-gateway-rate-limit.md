---
doc_id: runbook-llm-gateway-rate-limit
doc_type: runbook
title: 'llm-gateway: provider rate limit exhaustion'
services:
- llm-gateway
metadata:
  root_cause_category: rate_limit_exhaustion
---

llm-gateway is returning 429s or queuing requests for an extended time. This happens when aggregate request volume across chatbot-orchestrator, rag-retriever, voicebot-asr, and recommendation-engine exceeds the provider's per-minute token or request quota.

Fix: check the llm-gateway dashboard for per-consumer request volume to identify which caller spiked. Enable the degraded-mode feature flag to shed recommendation-engine traffic first (lowest customer impact), then contact the provider to request a temporary quota increase if the spike is expected to continue.
