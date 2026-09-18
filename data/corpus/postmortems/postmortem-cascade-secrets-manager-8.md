---
doc_id: postmortem-cascade-secrets-manager-8
doc_type: postmortem
title: 'Postmortem: secrets-manager cascade (a batch or background job no longer producing
  fresh output)'
services:
- secrets-manager
- api-gateway
- auth-service
- chatbot-orchestrator
- checkout-api
- ci-pipeline
- llm-gateway
metadata:
  root_cause_service: secrets-manager
  root_cause_category: job_failure
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

Summary: secrets-manager experienced a batch or background job no longer producing fresh output. This produced symptoms in 6 dependent services at once: api-gateway, auth-service, chatbot-orchestrator, checkout-api, ci-pipeline, llm-gateway.

Root cause: the job has been failing without alerting directly on job failure.

On-call for several of the affected services were paged independently before the shared root cause on secrets-manager was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on secrets-manager rather than relying on downstream symptoms to surface a shared root cause.
