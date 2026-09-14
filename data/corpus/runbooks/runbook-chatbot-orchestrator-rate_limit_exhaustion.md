---
doc_id: runbook-chatbot-orchestrator-rate_limit_exhaustion
doc_type: runbook
title: 'chatbot-orchestrator: rate limit exhaustion'
services:
- chatbot-orchestrator
metadata:
  root_cause_category: rate_limit_exhaustion
---

chatbot-orchestrator is showing requests queueing or being rejected outright. Check llm-gateway first -- chatbot-orchestrator depends on it directly. Check the chatbot-orchestrator dashboard and recent deploys via ci-pipeline before assuming the fault is in chatbot-orchestrator itself.

Likely cause: aggregate request volume exceeded the provider's quota.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting chatbot-orchestrator -- a restart will not fix rate limit exhaustion if the underlying condition is still present.

Blast radius: Support chatbot unavailable; customers fall back to human support.
