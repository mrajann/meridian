---
doc_id: runbook-api-gateway-5xx_errors
doc_type: runbook
title: 'api-gateway: 5xx errors'
services:
- api-gateway
metadata:
  root_cause_category: 5xx_errors
---

api-gateway is showing an elevated 5xx error rate. Check auth-service first -- api-gateway depends on it directly. Check the api-gateway dashboard and recent deploys via ci-pipeline before assuming the fault is in api-gateway itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting api-gateway -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: All web and mobile traffic blocked. Complete customer-facing outage.
