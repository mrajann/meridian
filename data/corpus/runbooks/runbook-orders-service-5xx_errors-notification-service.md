---
doc_id: runbook-orders-service-5xx_errors-notification-service
doc_type: runbook
title: 'orders-service: 5xx errors (notification-service root cause)'
services:
- orders-service
metadata:
  root_cause_category: 5xx_errors__notification-service
---

orders-service is showing an elevated 5xx error rate. Check the orders-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: notification-service is timing out on a synchronous confirmation call that should be async.

Fix: check notification-service health; consider making this call fire-and-forget if it recurs.
