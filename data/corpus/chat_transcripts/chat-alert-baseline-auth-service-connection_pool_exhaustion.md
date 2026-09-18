---
doc_id: chat-alert-baseline-auth-service-connection_pool_exhaustion
doc_type: chat_transcript
title: '#incidents: auth-service alert discussion'
services:
- auth-service
metadata:
  root_cause_service: auth-service
---

[+0m] @maya: paged for auth-service, requests stalling while waiting on a database connection
[+2m] @sam: looking now
[+4m] @maya: can confirm, checking dependencies
[+9m] @maya: found the runbook for this, running the fix now
[+14m] @sam: confirmed, back to normal
