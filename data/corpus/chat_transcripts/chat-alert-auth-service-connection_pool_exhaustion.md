---
doc_id: chat-alert-auth-service-connection_pool_exhaustion
doc_type: chat_transcript
title: '#incidents: auth-service alert discussion'
services:
- auth-service
metadata:
  root_cause_service: auth-service
---

[+0m] @arun: paged for auth-service, requests stalling while waiting on a database connection
[+2m] @lin: looking now
[+4m] @arun: can confirm, checking dependencies
[+9m] @arun: found the runbook for this, running the fix now
[+14m] @lin: confirmed, back to normal
