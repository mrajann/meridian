---
doc_id: runbook-baseline-cart-service-deploy_regression
doc_type: runbook
title: 'cart-service: deploy regression'
services:
- cart-service
metadata:
  root_cause_category: deploy_regression
---

cart-service is showing a symptom that started immediately after a deploy. Check redis-cache first -- cart-service depends on it directly. Check the cart-service dashboard and recent deploys via ci-pipeline before assuming the fault is in cart-service itself.

Likely cause: the most recent deploy introduced a regression.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting cart-service -- a restart will not fix deploy regression if the underlying condition is still present.

Blast radius: Customers cannot add items to cart or see incorrect cart contents.
