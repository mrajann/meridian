---
doc_id: runbook-mobile-api-checkout-api
doc_type: runbook
title: 'mobile-api: an elevated 5xx error rate (checkout-api root cause)'
services:
- mobile-api
metadata:
  root_cause_category: 5xx_errors__checkout-api
---

mobile-api is showing an elevated 5xx error rate. Check the mobile-api dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: checkout-api is degraded or unavailable, so mobile-api's calls to it are failing or timing out.

Fix: check checkout-api health directly before touching mobile-api itself.
