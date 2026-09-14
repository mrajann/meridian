---
doc_id: runbook-api-gateway-latency_spike
doc_type: runbook
title: 'api-gateway: latency spike'
services:
- api-gateway
metadata:
  root_cause_category: latency_spike
---

api-gateway is showing p99 latency above its SLO target. Check auth-service first -- api-gateway depends on it directly. Check the api-gateway dashboard and recent deploys via ci-pipeline before assuming the fault is in api-gateway itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting api-gateway -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: All web and mobile traffic blocked. Complete customer-facing outage.
