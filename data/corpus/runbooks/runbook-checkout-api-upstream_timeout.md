---
doc_id: runbook-checkout-api-upstream_timeout
doc_type: runbook
title: 'checkout-api: upstream timeout'
services:
- checkout-api
metadata:
  root_cause_category: upstream_timeout
---

checkout-api is showing elevated latency or errors tracing to one specific upstream call. Check auth-service first -- checkout-api depends on it directly. Check the checkout-api dashboard and recent deploys via ci-pipeline before assuming the fault is in checkout-api itself.

Likely cause: a synchronous call to a slow or degraded upstream is blocking the request path.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting checkout-api -- a restart will not fix upstream timeout if the underlying condition is still present.

Blast radius: All revenue. Complete outage means no orders can be placed.
