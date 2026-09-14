---
doc_id: chat-alert-analytics-api-connection_pool_exhaustion-unmatched
doc_type: chat_transcript
title: '#incidents: analytics-api alert discussion'
services:
- analytics-api
metadata:
  root_cause_service: analytics-api
---

[+0m] @priya: paged for analytics-api, requests stalling while waiting on a database connection
[+2m] @dev: looking now
[+4m] @priya: can confirm, checking dependencies
[+9m] @priya: couldn't find a runbook for this exact symptom
[+15m] @dev: tracked it down manually, let's write a runbook once this is resolved
