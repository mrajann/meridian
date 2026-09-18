---
doc_id: runbook-baseline-web-frontend-deploy_regression
doc_type: runbook
title: 'web-frontend: deploy regression'
services:
- web-frontend
metadata:
  root_cause_category: deploy_regression
---

web-frontend is showing a symptom that started immediately after a deploy. Check api-gateway first -- web-frontend depends on it directly. Check the web-frontend dashboard and recent deploys via ci-pipeline before assuming the fault is in web-frontend itself.

Likely cause: the most recent deploy introduced a regression.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting web-frontend -- a restart will not fix deploy regression if the underlying condition is still present.

Blast radius: Customers cannot browse or check out on the website. Mobile app unaffected.
