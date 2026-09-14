---
doc_id: chat-alert-catalog-service-latency_spike-unmatched
doc_type: chat_transcript
title: '#incidents: catalog-service alert discussion'
services:
- catalog-service
metadata:
  root_cause_service: catalog-service
---

[+0m] @maya: paged for catalog-service, p99 latency above its SLO target
[+2m] @sam: looking now
[+4m] @maya: can confirm, checking dependencies
[+9m] @maya: couldn't find a runbook for this exact symptom
[+15m] @sam: tracked it down manually, let's write a runbook once this is resolved
