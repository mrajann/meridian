---
doc_id: runbook-baseline-shipping-service-schema_mismatch
doc_type: runbook
title: 'shipping-service: schema mismatch'
services:
- shipping-service
metadata:
  root_cause_category: schema_mismatch
---

shipping-service is showing requests failing validation unexpectedly. Check orders-service first -- shipping-service depends on it directly. Check the shipping-service dashboard and recent deploys via ci-pipeline before assuming the fault is in shipping-service itself.

Likely cause: a caller is still sending a previous version of the request schema.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting shipping-service -- a restart will not fix schema mismatch if the underlying condition is still present.

Blast radius: Orders cannot be dispatched for shipping. Order placement unaffected.
