---
doc_id: runbook-web-frontend-5xx_errors
doc_type: runbook
title: 'web-frontend: 5xx errors'
services:
- web-frontend
metadata:
  root_cause_category: 5xx_errors
---

web-frontend is showing an elevated 5xx error rate. Check api-gateway first -- web-frontend depends on it directly. Check the web-frontend dashboard and recent deploys via ci-pipeline before assuming the fault is in web-frontend itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting web-frontend -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Customers cannot browse or check out on the website. Mobile app unaffected.
