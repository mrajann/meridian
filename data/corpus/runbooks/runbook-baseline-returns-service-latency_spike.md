---
doc_id: runbook-baseline-returns-service-latency_spike
doc_type: runbook
title: 'returns-service: latency spike'
services:
- returns-service
metadata:
  root_cause_category: latency_spike
---

returns-service is showing p99 latency above its SLO target. Check orders-service first -- returns-service depends on it directly. Check the returns-service dashboard and recent deploys via ci-pipeline before assuming the fault is in returns-service itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting returns-service -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Customers cannot initiate returns. No impact to ordering or shipping.
