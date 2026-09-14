---
doc_id: runbook-checkout-5xx-database
doc_type: runbook
title: 'checkout-api 5xx: database root cause'
services:
- checkout-api
- postgres-primary
metadata:
  root_cause_category: connection_pool_exhaustion
---

checkout-api is returning elevated 5xx rates or p99 latency above its 400ms SLO target. Follow this triage sequence before escalating:

1. Check the checkout-api dashboard for error rate and latency by endpoint.
2. Check recent deploys via ci-pipeline -- roll back if a deploy correlates with the onset.
3. Check upstream dependency health: auth-service, inventory-service, pricing-engine, postgres-primary, and stripe-gateway.
4. Confirm current on-call for payments-platform is aware before taking any remediation action, since checkout-api is revenue-critical.
5. Narrow down which specific upstream dependency is the actual source before applying a fix -- do not guess.

Root cause: postgres-primary. Database connections are maxed out under sustained load, so checkout-api's queries queue until they time out.

Fix: check `pg_stat_activity` on postgres-primary against `max_connections`, then restart the connection pooler and raise the pool size if needed.
