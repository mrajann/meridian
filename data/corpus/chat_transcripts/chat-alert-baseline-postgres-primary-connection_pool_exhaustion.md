---
doc_id: chat-alert-baseline-postgres-primary-connection_pool_exhaustion
doc_type: chat_transcript
title: '#incidents: postgres-primary alert discussion'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
---

[+0m] @maya: paged for postgres-primary, requests stalling while waiting on a database connection
[+2m] @sam: looking now
[+4m] @maya: can confirm, checking dependencies
[+9m] @maya: found the runbook for this, running the fix now
[+14m] @sam: confirmed, back to normal
