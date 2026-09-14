---
doc_id: alert-checkout-api-connection_pool_exhaustion
doc_type: alert
title: 'checkout-api: requests stalling while waiting on a database connection'
services:
- checkout-api
metadata:
  root_cause_service: checkout-api
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-checkout-5xx-database
  has_matching_runbook: true
  fragile_service: null
---

checkout-api: requests stalling while waiting on a database connection. Onset was within the last monitoring window -- investigate before it breaches SLO further.
