---
doc_id: runbook-returns-service-orders-service
doc_type: runbook
title: 'returns-service: an elevated 5xx error rate (orders-service root cause)'
services:
- returns-service
metadata:
  root_cause_category: 5xx_errors__orders-service
---

returns-service is showing an elevated 5xx error rate. Check the returns-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: orders-service is degraded or unavailable, so returns-service's calls to it are failing or timing out.

Fix: check orders-service health directly before touching returns-service itself.
