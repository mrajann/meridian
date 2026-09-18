---
doc_id: runbook-chatbot-orchestrator-llm-gateway
doc_type: runbook
title: 'chatbot-orchestrator: requests queueing or being rejected outright (llm-gateway
  root cause)'
services:
- chatbot-orchestrator
metadata:
  root_cause_category: rate_limit_exhaustion__llm-gateway
---

chatbot-orchestrator is showing requests queueing or being rejected outright. Check the chatbot-orchestrator dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: llm-gateway is degraded or unavailable, so chatbot-orchestrator's calls to it are failing or timing out.

Fix: check llm-gateway health directly before touching chatbot-orchestrator itself.
