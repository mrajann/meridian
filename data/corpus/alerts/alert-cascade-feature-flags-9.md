---
doc_id: alert-cascade-feature-flags-9
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- api-gateway
- chatbot-orchestrator
- llm-gateway
- mobile-api
- rag-retriever
- recommendation-engine
metadata:
  root_cause_service: feature-flags
  root_cause_category: misconfiguration
  correct_runbook: runbook-cascade-root-cause-feature-flags-misconfiguration
  has_matching_runbook: true
  affected_services:
  - api-gateway
  - chatbot-orchestrator
  - llm-gateway
  - mobile-api
  - rag-retriever
  - recommendation-engine
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across api-gateway, chatbot-orchestrator, llm-gateway, mobile-api, rag-retriever, recommendation-engine, all starting within the same 60-second window. All depend on feature-flags, directly or transitively.
