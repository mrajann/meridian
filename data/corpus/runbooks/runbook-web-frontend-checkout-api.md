---
doc_id: runbook-web-frontend-checkout-api
doc_type: runbook
title: 'web-frontend: an elevated 5xx error rate (checkout-api root cause)'
services:
- web-frontend
metadata:
  root_cause_category: 5xx_errors__checkout-api
---

web-frontend is showing an elevated 5xx error rate. Check the web-frontend dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: checkout-api is degraded or unavailable, so web-frontend's calls to it are failing or timing out.

Fix: check checkout-api health directly before touching web-frontend itself.
