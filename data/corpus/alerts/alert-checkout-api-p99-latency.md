---
doc_id: alert-checkout-api-p99-latency
doc_type: alert
title: checkout-api p99 latency 2400ms, threshold 400ms
services:
- checkout-api
metadata:
  root_cause_service: postgres-primary
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-checkout-5xx-database
  has_matching_runbook: true
  fragile_service: postgres-primary
---

checkout-api p99 latency 2400ms, threshold 400ms. Error rate also elevated (4.1%, threshold 1%). Onset was sudden, coinciding with the start of the flash sale. Application logs show requests stalled waiting on the database connection pool -- connection pool exhausted.
