---
doc_id: runbook-baseline-llm-gateway-latency_spike
doc_type: runbook
title: 'llm-gateway: latency spike'
services:
- llm-gateway
metadata:
  root_cause_category: latency_spike
---

llm-gateway is showing p99 latency above its SLO target. Check secrets-manager first -- llm-gateway depends on it directly. Check the llm-gateway dashboard and recent deploys via ci-pipeline before assuming the fault is in llm-gateway itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting llm-gateway -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: All AI-layer features (chatbot, voicebot, recommendations, RAG) degrade or fail.
