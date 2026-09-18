---
doc_id: runbook-baseline-llm-gateway-upstream_timeout
doc_type: runbook
title: 'llm-gateway: upstream timeout'
services:
- llm-gateway
metadata:
  root_cause_category: upstream_timeout
---

llm-gateway is showing elevated latency or errors tracing to one specific upstream call. Check secrets-manager first -- llm-gateway depends on it directly. Check the llm-gateway dashboard and recent deploys via ci-pipeline before assuming the fault is in llm-gateway itself.

Likely cause: a synchronous call to a slow or degraded upstream is blocking the request path.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting llm-gateway -- a restart will not fix upstream timeout if the underlying condition is still present.

Blast radius: All AI-layer features (chatbot, voicebot, recommendations, RAG) degrade or fail.
