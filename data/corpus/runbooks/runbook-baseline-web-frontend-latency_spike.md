---
doc_id: runbook-baseline-web-frontend-latency_spike
doc_type: runbook
title: 'web-frontend: latency spike'
services:
- web-frontend
metadata:
  root_cause_category: latency_spike
---

web-frontend is showing p99 latency above its SLO target. Check api-gateway first -- web-frontend depends on it directly. Check the web-frontend dashboard and recent deploys via ci-pipeline before assuming the fault is in web-frontend itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting web-frontend -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Customers cannot browse or check out on the website. Mobile app unaffected.
