---
doc_id: runbook-returns-service-5xx_errors
doc_type: runbook
title: 'returns-service: 5xx errors'
services:
- returns-service
metadata:
  root_cause_category: 5xx_errors
---

returns-service is showing an elevated 5xx error rate. Check orders-service first -- returns-service depends on it directly. Check the returns-service dashboard and recent deploys via ci-pipeline before assuming the fault is in returns-service itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting returns-service -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Customers cannot initiate returns. No impact to ordering or shipping.
