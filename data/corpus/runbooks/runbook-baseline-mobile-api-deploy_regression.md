---
doc_id: runbook-baseline-mobile-api-deploy_regression
doc_type: runbook
title: 'mobile-api: deploy regression'
services:
- mobile-api
metadata:
  root_cause_category: deploy_regression
---

mobile-api is showing a symptom that started immediately after a deploy. Check api-gateway first -- mobile-api depends on it directly. Check the mobile-api dashboard and recent deploys via ci-pipeline before assuming the fault is in mobile-api itself.

Likely cause: the most recent deploy introduced a regression.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting mobile-api -- a restart will not fix deploy regression if the underlying condition is still present.

Blast radius: Mobile app customers cannot browse or check out. Web storefront unaffected.
