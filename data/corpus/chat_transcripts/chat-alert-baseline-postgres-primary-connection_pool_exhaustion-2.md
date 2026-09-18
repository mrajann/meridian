---
doc_id: chat-alert-baseline-postgres-primary-connection_pool_exhaustion-2
doc_type: chat_transcript
title: '#incidents: postgres-primary alert discussion'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
---

[+0m] @sam: paged for postgres-primary, requests stalling while waiting on a database connection
[+2m] @jules: looking now
[+4m] @sam: can confirm, checking dependencies
[+9m] @sam: found the runbook for this, running the fix now
[+14m] @jules: confirmed, back to normal
