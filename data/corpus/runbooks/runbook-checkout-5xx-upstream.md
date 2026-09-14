---
doc_id: runbook-checkout-5xx-upstream
doc_type: runbook
title: 'checkout-api 5xx: upstream payment processor root cause'
services:
- checkout-api
- stripe-gateway
metadata:
  root_cause_category: upstream_payment_timeout
---

checkout-api is returning elevated 5xx rates or p99 latency above its 400ms SLO target. Follow this triage sequence before escalating:

1. Check the checkout-api dashboard for error rate and latency by endpoint.
2. Check recent deploys via ci-pipeline -- roll back if a deploy correlates with the onset.
3. Check upstream dependency health: auth-service, inventory-service, pricing-engine, postgres-primary, and stripe-gateway.
4. Confirm current on-call for payments-platform is aware before taking any remediation action, since checkout-api is revenue-critical.
5. Narrow down which specific upstream dependency is the actual source before applying a fix -- do not guess.

Root cause: stripe-gateway. The payment processor is slow or erroring, so checkout-api's own latency and error rate rise in lockstep.

Fix: check status.stripe.com and the integration dashboard, then switch checkout-api to the backup payment processor via feature-flags if Stripe confirms an incident.
