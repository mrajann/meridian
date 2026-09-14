---
doc_id: runbook-shipping-service-5xx_errors
doc_type: runbook
title: 'shipping-service: 5xx errors'
services:
- shipping-service
metadata:
  root_cause_category: 5xx_errors
---

shipping-service is showing an elevated 5xx error rate. Check orders-service first -- shipping-service depends on it directly. Check the shipping-service dashboard and recent deploys via ci-pipeline before assuming the fault is in shipping-service itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting shipping-service -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Orders cannot be dispatched for shipping. Order placement unaffected.
