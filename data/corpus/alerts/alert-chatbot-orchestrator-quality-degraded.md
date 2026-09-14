---
doc_id: alert-chatbot-orchestrator-quality-degraded
doc_type: alert
title: 'chatbot-orchestrator: response quality score below threshold'
services:
- chatbot-orchestrator
metadata:
  root_cause_service: llm-gateway
  root_cause_category: quality_degradation
  correct_runbook: runbook-llm-gateway-quality-degradation
  has_matching_runbook: true
  fragile_service: llm-gateway
---

Automated response-quality scoring for chatbot-orchestrator dropped from a 4.6 to a 2.9 rolling average over the last two hours. No increase in error rate, latency, or timeout count. Customer complaint volume for the support chatbot is rising.
