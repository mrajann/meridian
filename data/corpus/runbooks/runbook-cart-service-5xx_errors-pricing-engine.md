---
doc_id: runbook-cart-service-5xx_errors-pricing-engine
doc_type: runbook
title: 'cart-service: 5xx errors (pricing-engine root cause)'
services:
- cart-service
metadata:
  root_cause_category: 5xx_errors__pricing-engine
---

cart-service is showing an elevated 5xx error rate. Check the cart-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: pricing-engine is timing out, so cart totals cannot be computed.

Fix: check pricing-engine health -- cart-service has no fallback pricing path.
