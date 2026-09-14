---
doc_id: runbook-cart-service-5xx_errors-inventory-service
doc_type: runbook
title: 'cart-service: 5xx errors (inventory-service root cause)'
services:
- cart-service
metadata:
  root_cause_category: 5xx_errors__inventory-service
---

cart-service is showing an elevated 5xx error rate. Check the cart-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: inventory-service is timing out, so stock checks on add-to-cart are failing.

Fix: check inventory-service health -- cart-service cannot confirm availability without it.
