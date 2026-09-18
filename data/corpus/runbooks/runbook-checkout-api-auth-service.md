---
doc_id: runbook-checkout-api-auth-service
doc_type: runbook
title: 'checkout-api: requests stalling while waiting on a database connection (auth-service
  root cause)'
services:
- checkout-api
metadata:
  root_cause_category: connection_pool_exhaustion__auth-service
---

checkout-api is showing requests stalling while waiting on a database connection. Check the checkout-api dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: auth-service is degraded or unavailable, so checkout-api's calls to it are failing or timing out.

Fix: check auth-service health directly before touching checkout-api itself.
