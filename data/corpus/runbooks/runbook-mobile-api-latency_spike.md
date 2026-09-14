---
doc_id: runbook-mobile-api-latency_spike
doc_type: runbook
title: 'mobile-api: latency spike'
services:
- mobile-api
metadata:
  root_cause_category: latency_spike
---

mobile-api is showing p99 latency above its SLO target. Check api-gateway first -- mobile-api depends on it directly. Check the mobile-api dashboard and recent deploys via ci-pipeline before assuming the fault is in mobile-api itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting mobile-api -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Mobile app customers cannot browse or check out. Web storefront unaffected.
