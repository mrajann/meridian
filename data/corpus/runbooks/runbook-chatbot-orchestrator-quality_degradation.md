---
doc_id: runbook-chatbot-orchestrator-quality_degradation
doc_type: runbook
title: 'chatbot-orchestrator: quality degradation'
services:
- chatbot-orchestrator
metadata:
  root_cause_category: quality_degradation
---

chatbot-orchestrator is showing output quality dropping with no traditional error signal. Check llm-gateway first -- chatbot-orchestrator depends on it directly. Check the chatbot-orchestrator dashboard and recent deploys via ci-pipeline before assuming the fault is in chatbot-orchestrator itself.

Likely cause: a routing or model-version change degraded output quality without tripping a health check.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting chatbot-orchestrator -- a restart will not fix quality degradation if the underlying condition is still present.

Blast radius: Support chatbot unavailable; customers fall back to human support.
