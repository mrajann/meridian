---
doc_id: chat-postgres-primary-disk-full-cascade
doc_type: chat_transcript
title: '#incidents: multiple 5xx alerts firing'
services:
- postgres-primary
- checkout-api
- orders-service
- auth-service
metadata:
  root_cause_service: postgres-primary
---

[14:02] @priya: getting paged for checkout-api 5xx, anyone else?
[14:02] @dev: yeah orders-service just paged me too
[14:03] @priya: weird, unrelated services, must be two separate things
[14:04] @dev: auth-service alert just fired as well. this doesn't feel unrelated anymore
[14:05] @priya: checking auth-service logs... it's timing out on postgres queries
[14:05] @dev: same on my end for checkout-api, queries just hanging
[14:06] @maya: pulling up postgres-primary dashboard now
[14:07] @maya: disk is at 100%. this is one incident, not three
[14:07] @priya: ok stopping my checkout-api-only investigation, following maya's lead
[14:08] @maya: freeing space now, will update here
