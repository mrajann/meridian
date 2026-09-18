---
doc_id: alert-cascade-secrets-manager-8
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- api-gateway
- auth-service
- chatbot-orchestrator
- checkout-api
- ci-pipeline
- llm-gateway
metadata:
  root_cause_service: secrets-manager
  root_cause_category: job_failure
  correct_runbook: runbook-cascade-root-cause-secrets-manager-job_failure
  has_matching_runbook: true
  affected_services:
  - api-gateway
  - auth-service
  - chatbot-orchestrator
  - checkout-api
  - ci-pipeline
  - llm-gateway
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across api-gateway, auth-service, chatbot-orchestrator, checkout-api, ci-pipeline, llm-gateway, all starting within the same 60-second window. All depend on secrets-manager, directly or transitively.
