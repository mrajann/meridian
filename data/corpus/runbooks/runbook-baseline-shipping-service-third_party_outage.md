---
doc_id: runbook-baseline-shipping-service-third_party_outage
doc_type: runbook
title: 'shipping-service: third party outage'
services:
- shipping-service
metadata:
  root_cause_category: third_party_outage
---

shipping-service is showing requests to an external provider failing or timing out. Check orders-service first -- shipping-service depends on it directly. Check the shipping-service dashboard and recent deploys via ci-pipeline before assuming the fault is in shipping-service itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting shipping-service -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Orders cannot be dispatched for shipping. Order placement unaffected.
