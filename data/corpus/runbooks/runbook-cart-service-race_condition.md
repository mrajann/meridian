---
doc_id: runbook-cart-service-race_condition
doc_type: runbook
title: 'cart-service: race condition'
services:
- cart-service
metadata:
  root_cause_category: race_condition
---

cart-service is showing inconsistent or duplicated state under concurrent load. Check redis-cache first -- cart-service depends on it directly. Check the cart-service dashboard and recent deploys via ci-pipeline before assuming the fault is in cart-service itself.

Likely cause: two concurrent operations both read stale state before either write committed.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting cart-service -- a restart will not fix race condition if the underlying condition is still present.

Blast radius: Customers cannot add items to cart or see incorrect cart contents.
