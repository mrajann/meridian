---
doc_id: chat-search-service-zero-results-investigation
doc_type: chat_transcript
title: '#incidents: search returning zero results for some queries'
services:
- search-service
metadata:
  root_cause_service: search-service
---

[16:40] @arun: search-service alert, zero-result rate up for a subset of queries
[16:41] @lin: pulling up search-service-5xx runbook
[16:43] @lin: hold on, that runbook is about 5xx errors, we're not seeing any errors at all
[16:43] @arun: right, requests are succeeding, just returning empty result sets
[16:44] @lin: checked our runbook index, there isn't one for this specific symptom
[16:45] @arun: ok, treating this as unfamiliar territory then. checking the index rebuild job logs directly
[16:52] @arun: found it, rebuild job has been silently failing for 3 nights
[16:53] @lin: let's write a runbook for this once it's resolved so we're not doing this from scratch next time
