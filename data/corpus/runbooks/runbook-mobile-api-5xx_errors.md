---
doc_id: runbook-mobile-api-5xx_errors
doc_type: runbook
title: 'mobile-api: 5xx errors'
services:
- mobile-api
metadata:
  root_cause_category: 5xx_errors
---

mobile-api is showing an elevated 5xx error rate. Check api-gateway first -- mobile-api depends on it directly. Check the mobile-api dashboard and recent deploys via ci-pipeline before assuming the fault is in mobile-api itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting mobile-api -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Mobile app customers cannot browse or check out. Web storefront unaffected.
